#!/usr/bin/python
import datetime
import logging
import os
import sys

# Add the parent folder of the script to the path
scriptpath = os.path.realpath(__file__)
scriptdir = os.path.dirname(scriptpath)
parentdir = os.path.dirname(scriptdir)
sys.path.append(parentdir)

# Tell where to find the DJANGO settings.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "srm.settings")
from django.contrib.auth.models import User

from core.models import Generator, Sensor, Rule, RuleSet, RuleClass, RuleReferenceType, RuleReference
from tuning.models import Suppress, SuppressAddress, DetectionFilter, EventFilter
from util.xmlrpcserver import RPCServer
from util.config import Config

cache = {}
timeOut = int(Config.get("xmlrpc-server", "client-timeout"))

def requireAuth(function):
	"""Decorator for methods where it is required that the client is authenticated to use it.
	Checks if the token is found in the cache, and that it is new enough.
	
	If everything is fine, the function is called. Otherwise, a status=False and a 
	status-message is returned."""

	def inner(*args):
		if(len(args) <= 1):
			return {'status': False, 'message': "No token supplied"}
		elif(args[1] not in cache['session']):
			return {'status': False, 'message': "Invalid token"}
		elif(datetime.datetime.now() > cache['session'][args[1]]['time'] + datetime.timedelta(seconds=timeOut)):
			cache['session'].pop(args[1])
			return {'status': False, 'message': "Token has timed out."}
		else:
			cache['session'][args[1]]['time'] = datetime.datetime.now()
			return function(*args)
	return inner

class RPCInterface():
	def __init__(self):
		import string
		self.python_string = string
	
	####################################################################################################
	# WARNING: The debug* methods is a HUGE security liability, and MUST be removed before release.    #
	# TODO: Remove debug-methods from the xmlrpc-server.                                               #
	####################################################################################################
	def debugGetCache(self):
		d = {}
		for t in cache:
			d[t] = {}
			for e in cache[t]:
				d[t][e] = str(cache[t][e])
		return d
	####################################################################################################
	####################################################################################################
	
	def authenticate(self, sensorname, secret):
		d = {}
		d['status'] = False

		try:
			sensor = Sensor.objects.get(name=sensorname)
		except Sensor.DoesNotExist:
			d['message'] = "Sensor does not exist"
			return d
		
		if(sensor.user.check_password(secret) == False):
			d['message'] = "Secret is incorrect"
			return d
		
		d['status'] = True
		d['token'] = str(sensor.id) + "-" + User.objects.make_random_password()
		d['sensorID'] = sensor.id
		
		cache['session'][d['token']] = {}
		cache['session'][d['token']]['time'] = datetime.datetime.now()
		cache['session'][d['token']]['sensor'] = sensor
		
		sensor.user.last_login = datetime.datetime.now()
		sensor.user.save()

		return d
	
	@requireAuth
	def deAuthenticate(self, token):
		cache['session'].pop(token)
		return {'status': True, 'message': "Sessiontoken is destroyed."}
	
	@requireAuth
	def getRuleClasses(self, token):
		classes = {}
		for rc in RuleClass.objects.all():
			c = {}
			c['classtype'] = rc.classtype
			c['description'] = rc.description
			c['priority'] = rc.priority
			classes[rc.classtype] = c
		
		return {'status': True, 'classes': classes}
	
	@requireAuth
	def getGenerators(self, token):
		generators = {}
		for generator in Generator.objects.all():
			g = {}
			g['GID'] = generator.GID
			g['alertID'] = generator.alertID
			g['message'] = generator.message
			generators[str(generator.GID) + "-" + str(generator.alertID)] = g
		return {'status': True, 'generators': generators}
	
	@requireAuth
	def getReferenceTypes(self, token):
		referenceTypes = {}
		for rt in RuleReferenceType.objects.all():
			ref = {}
			ref['name'] = rt.name
			ref['urlPrefix'] = rt.urlPrefix
			referenceTypes[rt.name] = ref
		
		return {'status': True, 'referenceTypes': referenceTypes}
	
	@requireAuth
	def getRuleRevisions(self, token):
		sensor = cache['session'][token]['sensor']
		rulerevisions = {}
		
		for ruleSet in sensor.ruleSets.all():
			if(ruleSet.active):
				rulerevisions.update(ruleSet.getRuleRevisions(True))
		
		return {'status': True, 'revisions': rulerevisions}
	
	@requireAuth
	def getRuleSets(self, token):
		sensor = cache['session'][token]['sensor']

		sets = []
		rulesets = {}

		for rs in sensor.ruleSets.all():
			if(rs.active):
				sets.append(rs)
				sets.extend(rs.getChildSets())
		
		for rs in sets:
			ruleset = {}
			ruleset['name'] = rs.name
			ruleset['description'] = rs.description 
			rulesets[rs.name] = ruleset

		return {'status': True, 'rulesets': rulesets}
	
	@requireAuth
	def getRules(self, token, rulelist):
		maxRequestSize = int(Config.get("xmlrpc-server", "max-requestsize"))
		if(len(rulelist) > maxRequestSize):
			raise Exception("Cannot request more than %d rules" % maxRequestSize)
		
		rules = {}
		sensor = cache['session'][token]['sensor']

		for r in rulelist:
			rule = Rule.objects.get(SID=r)
			dictRule = {}
			dictRule['SID'] = rule.SID
			dictRule['rev'] = rule.revisions.last().rev
			dictRule['msg'] = rule.revisions.last().msg
			dictRule['raw'] = rule.revisions.last().raw
			dictRule['ruleset'] = rule.ruleSet.name
			dictRule['ruleclass'] = rule.ruleClass.classtype
			dictRule['references'] = rule.revisions.last().getReferences()
			
			eventFilter = None
			detectionFilter = None
			suppress = None

			s = sensor
			while s != None:
				try:
					eventFilter = s.eventFilters.get(rule=rule)
				except EventFilter.DoesNotExist:
					pass

				try:
					detectionFilter = s.detectionFilters.get(rule=rule)
				except DetectionFilter.DoesNotExist:
					pass

				try:
					suppress = s.suppress.get(rule=rule)
				except Suppress.DoesNotExist:
					pass
				
				s = s.parent
				
			if eventFilter:
				dictRule['eventFilter'] = {}
				dictRule['eventFilter']['type'] = eventFilter.eventFilterType
				dictRule['eventFilter']['track'] = eventFilter.track
				dictRule['eventFilter']['count'] = eventFilter.count
				dictRule['eventFilter']['seconds'] = eventFilter.seconds

			if detectionFilter:
				dictRule['detectionFilter'] = {}
				dictRule['detectionFilter']['track'] = detectionFilter.track
				dictRule['detectionFilter']['count'] = detectionFilter.count
				dictRule['detectionFilter']['seconds'] = detectionFilter.seconds
				
			if suppress:
				dictRule['suppress'] = {}
				dictRule['suppress']['track'] = suppress.track
				dictRule['suppress']['addresses'] = suppress.getAddresses()
			
			rules[str(rule.SID)] = dictRule
		
		return {'status': True, 'rules': rules}
	
	@requireAuth
	def ping(self, token):
		return {'status': True, 'Message': "Pong!"}
	
	def dummy(self, data):
		return str(type(data)) + ":" + str(data)

def startRPCServer():
	bindAddress = Config.get("xmlrpc-server", "address")
	bindPort = int(Config.get("xmlrpc-server", "port"))
	
	for s in ['session']:
		cache[s] = {}
	
	server_address = (bindAddress, bindPort) # (address, port)
	server = RPCServer(RPCInterface(), server_address)	
	sa = server.socket.getsockname()

	print "Serving HTTPS on", sa[0], "port", sa[1]
	server.startup()

if __name__ == '__main__':
	startRPCServer()
