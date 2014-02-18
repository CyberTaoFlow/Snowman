import logging

from django.db import models
from django.contrib.auth.models import User

"""This python-model contains the data-models for the core
data. This includes the Rules and revisions, Rulesets, RuleClasses,
RuleReferences and Sensors."""

class Generator(models.Model):
	"""The Generator class is to hold the data of gen-msg.conf. Generators,
	AlertID's and messages."""

	GID = models.IntegerField()
	alertID = models.IntegerField()
	message = models.TextField()
	
	def __repr__(self):
		return "<Generator GID:%d, alertID:%d, message:\"%s\">" % (self.GID, self.alertID, self.message)
	
	def __str__(self):
		return "<Generator GID:%d, alertID:%d>" % (self.GID, self.alertID)

class Rule(models.Model):
	"""The Rule class contains only some meta-info about a specific
	rule. The SID, if the rule should be active, and to which ruleset
	this rule should belong to is the relevant data to store here.
	
	The real data of the rule should be stored in a RuleRevision."""

	SID = models.IntegerField()
	active = models.BooleanField()
	generator = models.ForeignKey('Generator', related_name='rules')
	ruleSet = models.ForeignKey('RuleSet', related_name='rules')
	ruleClass = models.ForeignKey('RuleClass', related_name='rules')

	def __repr__(self):
		return "<Rule SID:%d, Active:%s, Set:%s, Class:%s>" % (self.SID, 
					str(self.active), self.ruleSet.name, self.ruleClass.classtype)

	def __str__(self):
		return "<Rule SID:%d>" % (self.SID)
	
	def updateRule(self, raw, rev = None, active = None, msg = None):
		"""This method recieves a rule, and if needed, creates a new RuleRevision object, and inserts into
		the list of revisions belonging to this rule. If the rev on the new rule is equal, or smaller than
		the last in revisions, nothing is done.
		
		If rev/active/msg is not supplied, they will be extracted from the raw string"""

		logger = logging.getLogger(__name__)

		# TODO: Parse raw for arguments that is not supplied by caller.
		
		# Try to grab the latest revision from the database
		try:
			lastRev = self.revisions.latest(field_name = 'rev')
		except RuleRevision.DoesNotExist:
			lastRev = None
		
		# If no revisions are found, or the last revision is smaller than the new one,
		#   add the new revision to the database.
		if(lastRev == None or int(lastRev.rev) < int(rev)):
			rev = RuleRevision.objects.create(rule=self, rev=int(rev), active=active, msg=msg, raw=raw)
			logger.debug("Updated rule-revision:" + str(rev))
			return rev
		
		return None

class RuleClass(models.Model):
	"""A ruleclass have a name, and a priority. All Rule objects should
	be a part of a RuleClass"""

	classtype = models.CharField(max_length=80)
	description = models.TextField()
	priority = models.IntegerField()
	
	def __repr__(self):
		return "<RuleClass Type:%s, Description:'%s', Priority:%d>" % (self.classtype, self.description, self.priority)

	def __str__(self):
		return "<RuleClass Type:%s, Priority:%d>" % (self.classtype, self.priority)

class RuleReference(models.Model):
	"""A RuleReference contains information on where to find more info
	about a specific rule. It is of a certain type (which contains an
	urlPrefix), and a reference."""
	
	reference = models.CharField(max_length=80)
	referenceType = models.ForeignKey('RuleReferenceType', related_name='references')
	rulerevision = models.ForeignKey('RuleRevision', related_name='references')

	def __repr__(self):
		return "<RuleReference Type:%s, Reference:'%s', Rule(SID/rev):%d/%d>" % (self.referenceType.name, 
					self.reference, self.rulerevision.rule.SID, self.rulerevision.rev)

	def __str__(self):
		return "<RuleReference Type:%s, Reference:'%s', Rule(SID/rev):%d/%d>" % (self.referenceType.name, 
					self.reference, self.rulerevision.rule.SID, self.rulerevision.rev)

class RuleReferenceType(models.Model):
	""" RuleReferenceType is the different types a certain rulereference
	might be. It contains a name, which we find in the raw rules, and a
	urlPrefix """

	name = models.CharField(max_length=30)
	urlPrefix = models.CharField(max_length=80)

	def __repr__(self):
		return "<RuleReferenceType name:%s, urlPrefix:'%s'>" % (self.name, self.urlPrefix)

	def __str__(self):
		return "<RuleReferenceType name:%s, urlPrefix:'%s'>" % (self.name, self.urlPrefix)

class RuleRevision(models.Model):
	"""This class should represent a single revision of a rule. Every
	time a rule is updated, there should be created a new object of 
	this class.
	The active-field should signal if this revision is a revision we
	want to use. When a Rule is fetched, the revision with the highest
	rev that is active is selected as the correct rule to use."""

	rule = models.ForeignKey('Rule', related_name="revisions")
	active = models.BooleanField(default=True)
	rev = models.IntegerField()
	raw = models.TextField()
	msg = models.TextField()

	def __repr__(self):
		return "<RuleRevision SID:%d, rev:%d, active:%s raw:'%s', msg:'%s'>" % (self.rule.SID, self.rev, str(self.active), self.raw, self.msg)

	def __str__(self):
		return "<RuleRevision SID:%d, rev:%d, active:%s raw:'%s', msg:'%s'>" % (self.rule.SID, self.rev, str(self.active), self.raw, self.msg)

class RuleSet(models.Model):
	"""A RuleSet, is a set of rules. Alle Rule objects should have
	a reference to the ruleset they belong. The RuleSet object should
	only contain the metainfo for the set. Name, description, and 
	wheter it should be active or not."""

	name = models.CharField(max_length=30)
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

class Sensor(models.Model):
	"""A Sensor is information on one SnortSensor installation. It 
	contains name, address and the secret used for authentication."""

	parent = models.ForeignKey('Sensor', null=True, related_name='childSensors')
	name = models.CharField(max_length=30)
	user = models.ForeignKey(User, related_name='sensor')
	active = models.BooleanField(default=True)
	autonomous = models.BooleanField(default=False)
	ipAddress = models.CharField(max_length=38, default="")
	ruleSets = models.ManyToManyField('RuleSet', related_name='sensors')

	def __repr__(self):
		if(self.parent):
			return "<Sensor name:%s, parent:%s, active:%s, ipAddress:'%s', user:%s>" % (self.name, self.parent.name, str(self.active), self.ipAddress, self.user.username)
		else:
			return "<Sensor name:%s, parent:None, active:%s, ipAddress:'%s', user:%s>" % (self.name, str(self.active), self.ipAddress, self.user.username)

	def __str__(self):
		return "<Sensor name:%s, ipAddress:'%s'>" % (self.name, self.ipAddress)
