import datetime
import logging
import os
import re
import socket
import xmlrpclib

from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import utc

from util.config import Config
from util.configfile import ConfigFile
from util.constants import dbObjects
from util.tools import Replace, Timeout
from util.patterns import ConfigPatterns

from srm.settings import DATABASES

from core.exceptions import MissingObjectError

"""This module contains the data models for the core data.
This includes Rules and revisions, Rulesets, RuleClasses,
RuleReferences, Sensors and more."""

class Generator(models.Model):
	"""The Generator class is to hold the data of gen-msg.conf. Generators,
	AlertID's and messages."""

	GID = models.IntegerField()
	alertID = models.IntegerField()
	message = models.TextField()
	
	class Meta:
		# GID and alertID must be unique together
		unique_together = ('GID', 'alertID')	
	
	def __repr__(self):
		return "<Generator GID:%d, alertID:%d, message:\"%s\">" % (self.GID, self.alertID, self.message)
	
	def __str__(self):
		return "<Generator GID:%d, alertID:%d>" % (self.GID, self.alertID)

class Rule(models.Model):
	"""The Rule class only contains some meta-info about a specific
	rule: its SID, if the rule is active, and to which ruleset
	the rule belongs.
	
	Other specific data about rule is stored in RuleRevision objects."""

	SID = models.IntegerField(unique=True)
	active = models.BooleanField()
	generator = models.ForeignKey('Generator', related_name='rules')
	ruleSet = models.ForeignKey('RuleSet', related_name='rules')
	ruleClass = models.ForeignKey('RuleClass', related_name='rules')
	priority = models.IntegerField(null=True)

	def __repr__(self):
		return "<Rule SID:%d, Active:%s, Set:%s, Class:%s Priority:%s>" % (self.SID, 
					str(self.active), self.ruleSet.name, self.ruleClass.classtype, str(self.priority))

	def __str__(self):
		return "<Rule SID:%d>" % (self.SID)
	
	def getCurrentRevision(self):
		"""This method returns the most recent active rule-revision"""
		return self.revisions.filter(active=True).last()

	
	def updateRule(self, raw, rev = None, msg = None):
		"""This method receives a rule, creates a new RuleRevision object 
		(if needed), and inserts into the list of revisions belonging to 
		this rule. If the rev-number on the new rule is equal or lower than
		the last in revisions (i.e. the revision is not newer), nothing is done.
		
		If rev/active/msg is not passed, they will be extracted from the raw string.
		
		Returns new revision object if one is created, None otherwise."""

		logger = logging.getLogger(__name__)

		if rev is None or msg is None:
			# At least one parameter is missing, parse rulestring:
			# Construct a regex to match all elements a raw rulestring 
			# must have in order to be considered a valid rule
			# (sid, rev, message and classtype):
			result = re.match(ConfigPatterns.RULE, raw)
			rev = rev or result.group(3)
			msg = msg or result.group(4)
		
		# Try to grab the latest revision from the database
		try:
			lastRev = self.revisions.latest(field_name = 'rev')
		except RuleRevision.DoesNotExist:
			lastRev = None
		
		# If no revisions are found, or the last revision is lower than the new one,
		#   add the new revision to the database.
		if(lastRev == None or int(lastRev.rev) < int(rev)):
			
			maxRevisions = int(Config.get("update", "maxRevisions"))
			activateNewRevisions = Config.get("update", "activateNewRevisions")

			if activateNewRevisions == "true":
				activate = True
			else:
				activate = False
			
			# Remove filters from raw string before storage:
			replace = Replace("")			
			filters = ""
			
			raw = re.sub(r'detection_filter:.*?;', replace, raw)
			filters += replace.matched or ""
			raw = re.sub(r'threshold:.*?;', replace, raw)
			filters += replace.matched or ""
			
			raw = " ".join(raw.split())
			rev = RuleRevision.objects.create(rule=self, rev=int(rev), active=activate, msg=msg, raw=raw, filters=filters)
			logger.debug("Updated rule-revision:" + str(rev))
			
			# Delete old revisions:
			if maxRevisions > 0:
				while self.revisions.count() > maxRevisions:
					rev_min = self.revisions.all().aggregate(models.Min("rev"))["rev__min"]
					self.revisions.get(rev=rev_min).delete()

			return rev
		
		return None
	
	@staticmethod
	def getRuleRevisions():
		"""This method is to get a list over the latest rules/revisions. 

		This method creates a dictionary where the key is the SID, and the data is the rev of the newest rule.
		Useful for efficient comparing of the SID/rev with the new rules, without collecting all the rule-data
		from the database."""
		
		result = {}

		sidrev = RuleRevision.objects.values_list("rule__SID", "rev").all()
		
		for sid, rev in sidrev:
			try:
				if(result[sid] < rev):
					result[sid] = rev
			except KeyError:
				result[sid] = rev
		
		return result
	
class RuleClass(models.Model):
	"""Class modeling a rule classification (ruleclass). Contains the name, 
	description and priority for the ruleclass. All Rule objects should have
	a classification, and thus be connected to one RuleClass.
	
	The ruleclass name (classtype field) must be unique."""

	classtype = models.CharField(max_length=80,unique=True)
	description = models.TextField()
	priority = models.IntegerField()
	
	def __repr__(self):
		return "<RuleClass Type:%s, Description:'%s', Priority:%d>" % (self.classtype, self.description, self.priority)

	def __str__(self):
		return "<RuleClass Type:%s, Priority:%d>" % (self.classtype, self.priority)

class RuleReference(models.Model):
	"""A RuleReference contains information on where to find more info
	about a specific rule. It is of a certain type (which contains an
	urlPrefix), and a reference.
	
	Since multiple references can exist for one rule, all three fields
	together constitute a unique entry in the database."""
	
	reference = models.CharField(max_length=250)
	referenceType = models.ForeignKey('RuleReferenceType', related_name='references')
	rulerevision = models.ForeignKey('RuleRevision', related_name='references')

	class Meta:
		# Avoid duplicate entries
		unique_together = ('reference', 'referenceType', 'rulerevision')

	def __repr__(self):
		return "<RuleReference Type:%s, Reference:'%s', Rule(SID/rev):%d/%d>" % (self.referenceType.name, 
					self.reference, self.rulerevision.rule.SID, self.rulerevision.rev)

	def __str__(self):
		return "<RuleReference Type:%s, Reference:'%s', Rule(SID/rev):%d/%d>" % (self.referenceType.name, 
					self.reference, self.rulerevision.rule.SID, self.rulerevision.rev)

	def splitReference(self):
		return 0

class RuleReferenceType(models.Model):
	""" RuleReferenceType is the different types a certain rulereference
	might be. It contains a name, which we find in the raw rules, and a
	urlPrefix. Name must be unique in the database. """

	name = models.CharField(max_length=30, unique=True)
	urlPrefix = models.CharField(max_length=80)

	def __repr__(self):
		return "<RuleReferenceType name:%s, urlPrefix:'%s'>" % (self.name, self.urlPrefix)

	def __str__(self):
		return "<RuleReferenceType name:%s, urlPrefix:'%s'>" % (self.name, self.urlPrefix)

class RuleRevision(models.Model):
	"""Represents a single revision of a rule. Every
	time a rule is updated, a new revision object should be created.
	
	== FIELDS ==
	Raw: The text-string carrying the rule header and rule options. Known
	in this project as the rulestring.
	
	Msg: Alert message. 
	
	Active: The active-field determines if this revision is a revision we
	want to use. When a Rule is fetched, the revision with the highest
	rev that is active is selected as the correct rule to use.
	
	Filters: Inline filters such as detection filter and (now deprecated)
	threshold are stored as normal text-options in this field (as they
	appear in the original rulestring)."""

	raw = models.TextField()
	rev = models.IntegerField()
	msg = models.TextField()
	active = models.BooleanField(default=True)
	filters = models.TextField(default = "")
	rule = models.ForeignKey('Rule', related_name="revisions")

	def __repr__(self):
		return "<RuleRevision SID:%d, rev:%d, active:%s raw:'%s', msg:'%s'>" % (self.rule.SID, self.rev, str(self.active), self.raw, self.msg)

	def __str__(self):
		return "<RuleRevision SID:%d, rev:%d, active:%s raw:'%s', msg:'%s'>" % (self.rule.SID, self.rev, str(self.active), self.raw, self.msg)
	
	def getReferences(self):
		"""Returns a list of all the references that is related to this rule."""
		referenceList = []
		for ref in self.references.all():
			referenceList.append((ref.referenceType.name, ref.reference))
		return referenceList 

class RuleSet(models.Model):
	"""A RuleSet is a set of rules. All Rule objects must have
	a reference to the ruleset in which they belong. The RuleSet-
	object contains metainfo for the set: Name, description, and 
	whether it is active or not. A ruleset can also be part of
	another ruleset in a hierarchical structure. Name must be unique."""

	name = models.CharField(max_length=100, unique=True)
	parent = models.ForeignKey('RuleSet', null=True, related_name='childSets')
	description = models.TextField()
	active = models.BooleanField()

	def __repr__(self):
		if(self.parent):
			return "<RuleSet name:%s, parent:%s, active:%s description:'%s'>" % (self.name, self.parent.name, str(self.active), self.description)
		else:
			return "<RuleSet name:%s, parent:None, active:%s description:'%s'>" % (self.name, str(self.active), self.description)

	def __str__(self):
		return "<RuleSet name:%s>" % (self.name)
	
	def __len__(self):
		noRules = self.rules.count()
		for ruleSet in self.childSets.all():
			noRules += len(ruleSet)
		return noRules
	
	def getRuleRevisions(self, active):
		revisions = {}
		
		# Collect the rules in this ruleSet
		for rule in self.rules.all():
			if(active == None or active == rule.active):
				revisions[str(rule.SID)] = {}
				revisions[str(rule.SID)]['rule'] = rule
				revisions[str(rule.SID)]['rev'] = rule.getCurrentRevision()
		
		# Collect the sid of the rules in child-rulesets.
		for ruleSet in self.childSets.all():
			if ruleSet.active:
				revisions.update(ruleSet.getRuleRevisions(active))

		return revisions
	
	def getChildSets(self):
		"""This method returns a list of RuleSets, which is the children-sets (and their children)
		of this ruleset."""
		sets = []
		for childSet in self.childSets.all():
			if(childSet.active):
				sets.append(childSet)
				sets.extend(childSet.getChildSets())

		return sets	
	
	def getActiveRuleCount(self):
		"""This method counts the number of active rules in this ruleset, and any child-rulesets"""
		activeRulesCount = self.rules.filter(active=True).count()
		
		for child in self.childSets.all():
			activeRulesCount += child.getActiveRuleCount()
				
		return activeRulesCount
	
class Sensor(models.Model):
	"""A Sensor is information on one SnortSensor installation. It 
	contains name (unique), address and the secret used for authentication."""

	AVAILABLE = 0
	UNAVAILABLE = 1
	INACTIVE = 2
	AUTONOMOUS = 3
	UNKNOWN = 4
	
	parent = models.ForeignKey('Sensor', null=True, related_name='childSensors')
	name = models.CharField(max_length=30, unique=True)
	user = models.ForeignKey(User, related_name='sensor', null=True)
	active = models.BooleanField(default=True)
	autonomous = models.BooleanField(default=False)
	ipAddress = models.CharField(max_length=38, default="", null=True)
	ruleSets = models.ManyToManyField('RuleSet', related_name='sensors')
	lastChecked = models.DateTimeField(null=True, default=datetime.datetime.now())
	lastStatus = models.BooleanField(default=False)

	def __repr__(self):
		if(self.parent):
			return "<Sensor name:%s, parent:%s, active:%s, ipAddress:'%s'>" % (self.name, self.parent.name, str(self.active), self.ipAddress)
		else:
			return "<Sensor name:%s, parent:None, active:%s, ipAddress:'%s'>" % (self.name, str(self.active), self.ipAddress)

	def __str__(self):
		return "<Sensor name:%s, ipAddress:'%s'>" % (self.name, self.ipAddress)
	
	def pingSensor(self):
		"""This method checks the status of the sensor, to see if the snowman-clientd is running. It returns a dictionary,
		where 'status' contains a boolean value if the ping was successful, and 'message' contains a textual message of
		what happened."""
		logger = logging.getLogger(__name__)
		port = int(Config.get("sensor", "port"))
		timeout = int(Config.get("sensor", "pingTimeout"))
		sensor = xmlrpclib.Server("https://%s:%s" % (self.ipAddress, port))
		
		try:
			with Timeout(timeout):
				result = sensor.ping(self.name)
		except Timeout.Timeout:
			logger.warning("Ping to sensor %s timed out" % self.name)
			return {'status': False, 'message': "Ping to sensor timed out"}
		except socket.gaierror:
			logger.warning("Could not ping sensor %s. Address is malformed" % self.name)
			return {'status': False, 'message': "Could not ping sensor. Address is malformed"}
		except socket.error as e:
			logger.warning("Could not ping sensor %s. %s" % (self.name, str(e)))
			return {'status': False, 'message': "Could not ping sensor. %s" % str(e)}
		
		return result
	
	def requestUpdate(self):
		"""This method contacts the sensor, and asks it to do an update of its ruleset."""
		logger = logging.getLogger(__name__)
		port = int(Config.get("sensor", "port"))
		timeout = int(Config.get("sensor", "pingTimeout"))
		sensor = xmlrpclib.Server("https://%s:%s" % (self.ipAddress, port))
		
		try:
			with Timeout(timeout):
				result = sensor.startUpdate(self.name)
		except Timeout.Timeout:
			logger.warning("Ping to sensor timed out")
			return {'status': False, 'message': "Ping to sensor timed out"}
		except socket.gaierror:
			logger.warning("Could not ping sensor. Address is malformed")
			return {'status': False, 'message': "Could not ping sensor. Address is malformed"}
		except socket.error as e:
			logger.warning("Could not ping sensor. %s" % str(e))
			return {'status': False, 'message': "Could not ping sensor. %s" % str(e)}
		
		return result
	
	def getStatus(self):
		"""This method checks the latest status from the sensor-checks, and returns the result. It returns one of the
		following values:
			Sensor.AUTONOMOUS - This is an autonomous sensor
			Sensor.INACTIVE - This sensor is not active
			Sensor.UNKNOWN - The status of this sensor is not checked recently (ie: more than 5 minutes ago).
			Sensor.AVAILABLE - This sensor is reachable.
			Sensor.UNAVAILABLE - This sensor is not able to be reached.
		"""
		if(self.autonomous):
			return self.AUTONOMOUS
		elif(not self.active):
			return self.INACTIVE
		elif(self.lastChecked == None or self.lastChecked + datetime.timedelta(minutes=5) < datetime.datetime.utcnow().replace(tzinfo=utc)):
			return self.UNKNOWN
		elif(self.lastStatus):
			return self.AVAILABLE
		else:
			return self.UNAVAILABLE
	
	def getChildCount(self):
		"""This method counts the number of child-sensors (and their childs), and returns the total number."""
		childCount = 0
		for child in self.childSensors.all():
			childCount += 1
			childCount += child.getChildCount()

		return childCount
	
	@staticmethod
	def refreshStatus():
		"""This method updates the status-information of all the sensors that is not autonomous."""
		for sensor in Sensor.objects.exclude(name="All").filter(autonomous=False).all():
			status = sensor.pingSensor()
			sensor.lastStatus = status['status']
			sensor.lastChecked = datetime.datetime.utcnow().replace(tzinfo=utc)
			sensor.save()
			
	@staticmethod
	def getAllSensors():
		logger = logging.getLogger(__name__)
		sensorid = dbObjects.SENSORS_ALL
		# Get 'all sensors' object:
		try:
			return Sensor.objects.get(id=sensorid)
		except Sensor.DoesNotExist:
			message = "Object with id="+str(sensorid)+", representing all sensors does not exist in database."
			raise MissingObjectError(message)
			logger.critical(message)

class Comment(models.Model):
	"""
	Comment objects are used to track important events in the system, with who, what and when.
	"""
	user = models.ForeignKey(User, related_name='comments', null=True)
	time = models.DateTimeField(default = datetime.datetime.now())
	comment = models.TextField()
	type = models.CharField(max_length=100, default="")
	#foreignKey = models.IntegerField(null=True)
	
	def __repr__(self):
			return "<Comment user:%s, time:None, comment:%s, type:'%s', foreignKey:%s>" % (self.user, self.time, self.comment, self.foreignKey)

	def __str__(self):
		return "<Comment time:%s, type:'%s', comment:'%s'>" % (self.time, self.type, self.comment)
