from django.db import models
import logging
import re, os

from core.models import Generator, Rule, RuleSet, RuleRevision, RuleClass,\
	RuleReference, RuleReferenceType
	
from update.exceptions import BadFormatError, AbnormalRuleError

class RuleChanges(models.Model):
	"""RuleChanges represents the changes in the rulesets performed by the update-procedure.
	It references to a rule, what set it was a member in, what set it should become member in,
	and if it has been moved. When we know that the operator is happy about the set the rule
	is in, we can safely delete the corresponding RuleChanges object."""
	
	rule = models.ForeignKey(Rule)
	originalSet = models.ForeignKey(RuleSet, related_name="rulechangeoriginal")
	newSet = models.ForeignKey(RuleSet, related_name="rulechangenew")
	update = models.ForeignKey('Update', related_name="pendingChanges")
	moved = models.BooleanField()
	
	def __repr__(self):
		return "<RuleChanges SID:%d, fromSet:%s, toSet:%s, moved:%s>" % (self.rule.SID, 
				self.originalSet.name, self.newSet.name, str(self.moved))

	def __str__(self):
		return "<RuleChanges SID:%d, fromSet:%s, toSet:%s, moved:%s>" % (self.rule.SID, 
				self.originalSet.name, self.newSet.name, str(self.moved))

class Source(models.Model):
	"""A Source-object represents the different places we might get rule-updates from. If we have
	a stable url, we can even schedule regular updates from this source.
	
	The schedule is a cron-style string (30 0 * * 0 = 0:30 every sunday)"""
	
	name = models.CharField(max_length=40, unique=True)
	url = models.CharField(max_length=80)
	lastMd5 = models.CharField(max_length=80)
	schedule = models.CharField(max_length=40)
	
	def __repr__(self):
		return "<Source name:%s, schedule:%s, url:%s, lastMd5:%s>" % (self.name, str(self.schedule), self.url, self.lastMd5)
	
	def __str__(self):
		return "<Source name:%s, schedule:%s, url:%s>" % (self.name, str(self.schedule), self.url)
	
class Update(models.Model):
	"""An Update-object is representing a single update of rules. This update happened at a time,
	it has a source, and a link to all the RuleRevisions that were updated."""
	
	time = models.DateTimeField()
	source = models.ForeignKey('Source', related_name="updates")
	ruleRevisions = models.ManyToManyField(RuleRevision)
	
	def __repr__(self):
		return "<Update source:%s, time:%s>" % (self.source.name, str(self.time))

	def __str__(self):
		return "<Update source:%s, time:%s>" % (self.source.name, str(self.time))

	def parseRuleFile(self, path, currentRules = None, rulesets = {}, ruleclasses = {}, generators = {}):
		"""This method opens a rule-file, and parses it for all the found rules, and updated the
		database with the new rules."""
		
		logger = logging.getLogger(__name__)		
		
		if not currentRules:
			currentRules = Rule.getRuleRevisions()
		
		rulefile = open(path, "r")
		for line in rulefile:
			# TODO: rule span multiple lines
			try:
				self.updateRule(line.rstrip("\n"), path, currentRules, rulesets, ruleclasses, generators)
			except AbnormalRuleError:
				logger.info("Skipping abnormal rule in '%s'" % path)
	
	def updateRule(self, raw, path, currentRules = {}, rulesets = {}, ruleclasses = {}, generators = {}):
		"""This method takes a raw rule-string, parses it, and if it is a new rule, we 
		update the database.
		
		currentRules can be supplied (containing a list of all SID's as keys, and revs as data)
		to make it quicker to see if the current rule is newer than the ones already in the database.
		
		rulesets/ruleclasses is used as a cache to store the django-objects retrieved from the 
		database, so  that we in later calls to this method can use them for quicker access.
		(Memory is generally cheaper than dbAccess)"""
		
		logger = logging.getLogger(__name__)
		
		# If we find a gid-attribute, we are parsing the wrong file
		if re.match(r"(?=.*gid:(.*?);)",raw):
			# TODO: GID=1
			raise AbnormalRuleError
		
		# Get the filename of the current file:
		# (will throw AttributeError if invalid filename)
		filename = re.match(r"(.*)\.rules", os.path.split(path)[1]).group(1)
		
		# Construct a regex, so that we can extract all the interesting parameters from the raw rulestring.
		matchPattern = r"(.*)alert(?=.*sid:(\d+))(?=.*rev:(\d+))"
		matchPattern += r"(?=.*msg:\"(.*?)\";)"
		matchPattern += r"(?=.*classtype:(.*?);)"
		pattern = re.compile(matchPattern)
		
		# Regex to match ruleset name (not present in all rules)
		ruleset = re.match(r"(?=.*ruleset (.*?)[,;])", raw)
		
		# If the raw rule matched the regex: 
		result = pattern.match(raw)
		if(result):
			
			# Assign some helpful variable-names:
			if("#" in result.group(1)):
				raw = raw.lstrip("# ")
				ruleActive = False
			else:
				ruleActive = True
			ruleSID = result.group(2)
			ruleRev = result.group(3)
			
			# Ruleset name set to filename if not found in raw string:
			try:
				ruleSetName = ruleset.group(1)
			except AttributeError:
				ruleSetName = filename
			
			ruleMessage = result.group(4)
			ruleClassName = result.group(5)
			ruleGID = 1
			
			# If the rule is new, or is a newer version of a rule we already have:
			if(int(ruleSID) not in currentRules or int(ruleRev) > currentRules[int(ruleSID)]):
				# Grab the correct ruleset from cache/db, or create a new one if it doesn't exist.
				try:
					ruleset = rulesets[ruleSetName]
				except KeyError:
					try:
						ruleset = RuleSet.objects.get(name = ruleSetName)
					except RuleSet.DoesNotExist:
						ruleset = RuleSet.objects.create(name = ruleSetName, description=ruleSetName, active=True)
						logger.info("Created new ruleset (" + str(ruleset) + ") while importing rule")
					rulesets[ruleSetName] = ruleset
						
				# Grab the correct ruleclass from cache/db, or create a new one if doesn't exist.
				try:
					ruleclass = ruleclasses[ruleClassName]
				except KeyError:
					try:
						ruleclass = RuleClass.objects.get(classtype=ruleClassName)
					except RuleClass.DoesNotExist:
						ruleclass = RuleClass.objects.create(classtype=ruleClassName, description=ruleClassName, priority=4)
						logger.info("Created new ruleclass (" + str(ruleclass) + ") while importing rule")
					ruleclasses[ruleClassName] = ruleclass
					
				# Grab the correct generator from cache/db, or create a new one if doesn't exist.
				try:
					generator = generators[ruleGID]
				except KeyError:
					try:
						generator = Generator.objects.get(GID=ruleGID)
					except RuleClass.DoesNotExist:
						generator = Generator.objects.create(GID=ruleGID, alertID=1, message="Automaticly created during update")
						logger.info("Created new generator (" + str(generator) + ") while importing rule")
					ruleclasses[ruleClassName] = ruleclass
					
				# Grab the rule-object, or create a new one if it doesn't exist.
				try:
					rule = Rule.objects.get(SID=ruleSID)
					rule.active = ruleActive
					# TODO: Handle logic moving rule to new set
					rule.ruleClass = ruleclass
					rule.generator = generator
					rule.save()
					logger.debug("Updated rule:" + str(rule))
				except Rule.DoesNotExist:
					rule = Rule.objects.create(SID=int(ruleSID), generator=generator, active=ruleActive, ruleSet=ruleset, ruleClass=ruleclass)
					logger.debug("Created a new rule: " + str(rule))
				
				rev = rule.updateRule(raw, ruleRev, ruleActive, ruleMessage)
				if(rev):
					self.ruleRevisions.add(rev)
			else:
				logger.debug("Rule %s/%s is already up to date" % (ruleSID, ruleRev))
				
	def parseClassificationFile(self, path):
		"""Method for parsing classification.config. File is read line by line
		and classifications are updated in the database."""
		self.parseFile(self.updateClassification, path)()
		
	def parseGenMsgFile(self, path):
		"""Method for parsing gen-msg.map. File is read line by line
		and generators are updated in the database."""		
		self.parseFile(self.updateGenerator, path)()
		
	def parseReferenceConfig(self, path):
		"""Method for parsing reference.config which contains all ruleReferenceTypes.
		File is read line by line and generators are updated in the database."""
		self.parseFile(self.updateReference, path)()
		
	def updateReference(self, raw):
		logger = logging.getLogger(__name__)
		
		matchPattern = r"config reference: (.*) (http(s)?://.*)"
		pattern = re.compile(matchPattern)
		result = pattern.match(raw)
		
		if result:
			referenceType = result.group(1).strip()
			urlPrefix = result.group(2).strip()
			
			# Update or create:
			try:
				reference = RuleReferenceType.objects.get(name=referenceType)
				reference.urlPrefix = urlPrefix
				reference.save
			except RuleReferenceType.DoesNotExist:
				reference = RuleReferenceType.objects.create(name=referenceType, urlPrefix=urlPrefix)
				logger.debug("Created new ruleReferenceType: "+str(reference))
				
		
	def parseSidMsgFile(self, path):
		logger = logging.getLogger(__name__)
		
		try:
			# Create a dictionary with SID:revisionID for all rule revisions in this update
			updatedSIDs = {int(Rule.objects.get(id=x.rule_id).SID): x.id for x in self.ruleRevisions.all()}
			self.parseFile(self.updateSidMsg, path, updatedRules=updatedSIDs)()		
		except Rule.DoesNotExist:
			logger.error("Unexpected error: rule lookup failed!")
		
	def updateSidMsg(self, raw, updatedRules=None):
		"""The sid-msg.map file contains mappings between ruleSIDs, rule messages and ruleReferences.
		This method parses one line of this file (raw), and checks if the SID corresponds to a ruleRevision
		in this update. If this is the case, it updates the message in the ruleRevision and creates all ruleReferences.
		
		updatedRules is a dictionary with {SID:referenceID} entries. This is needed because rules are referenced
		by SID in sid-msg.map and by revisionID in Update.ruleRevisions."""
		
		logger = logging.getLogger(__name__)
		
		# Regex: Match a generator definition: SID || message (|| reference)*
		# SID is stored in group(1), and "message (|| reference)*" in group(2)
		matchPattern = r"(\d+) \|\| ((.*\|\|)* .*)"
		pattern = re.compile(matchPattern)
		result = pattern.match(raw)
		
		# If we have a match AND the SID is in updatedRules (rule was updated):
		if result:
			# We have a valid line, fetch the SID
			ruleSID = result.group(1)
			
			# If updatedRules exist and this SID exists in updatedRules:
			if updatedRules and (int(ruleSID) in updatedRules):
				revisionID = updatedRules[int(ruleSID)]
				
				# Get message and ruleReferences, if any
				data = result.group(2).split(" || ")				
				dataiter = iter(data)
				
				try:
					# Rule message is always the first element
					message = next(dataiter)
					RuleRevision.objects.get(id=revisionID).msg = message
					
					# Any succeeding elements are ruleReferences, formatted
					# with referenceType,referenceValue:
					for reference in dataiter:
						referenceData = reference.split(",")
						referenceType = referenceData[0]
						referenceValue = referenceData[1]
						
						referenceTypeID = RuleReferenceType.objects.get(name=referenceType).id
						RuleReference.objects.create(reference=referenceValue, referenceType_id=referenceTypeID,rulerevision_id=revisionID)
				except (StopIteration, IndexError):
					raise BadFormatError("Badly formatted sid-msg")
				except RuleReferenceType.DoesNotExist:
					logger.error("referenceType %s does not exist! RuleReference was not created." % referenceType)

	def updateClassification(self, raw):
		"""Method for updating the database with a new classification.
		Classification data consists of three comma-separated strings which are
		extracted with a regex, and split up in the three respective parts:
		classtype, description and priority. The classtype is looked up in the
		database and if found, the object is overwritten with the new data. Else,
		a new classification object is inserted into the database."""
		
		# Regex: Match "config classification: " (group 0),
		# and everything that comes after (group 1), which is the classification data. 
		matchPattern = r"config classification: (.*)"
		pattern = re.compile(matchPattern)
		result = pattern.match(raw)
		
		if result:
			# Split the data and store as separate strings
			classification = result.group(1).split(",")
			
			try:
				try:
					# Update existing classification
					ruleclassification = RuleClass.objects.get(classtype=classification[0])
					ruleclassification.description = classification[1]
					ruleclassification.priority = classification[2]
					ruleclassification.save()
				except RuleClass.DoesNotExist:
					# Add new classification
					RuleClass.objects.create(classtype=classification[0], description=classification[1], priority=classification[2])
			except IndexError:
				# If one or more indexes are invalid, the classification is badly formatted
				raise BadFormatError("Badly formatted rule classification")
				
	def updateGenerator(self, raw):
		"""Method for updating the database with a new generator.
		Generator data consists of two numbers and a message string, all three
		separated with a ||. All lines conforming to this pattern are split up
		in the three respective parts: GID (generatorID), alertID and message.
		The GID and alertID are looked up in the database and if found, the object 
		is overwritten with the new data. Else,	a new generator object is inserted 
		into the database."""
				
		# Regex: Match a generator definition: number || number || message
		# If the line matches, it is stored in group(0)
		matchPattern = r"(\d+ \|\| )+.*"
		pattern = re.compile(matchPattern)
		result = pattern.match(raw)
		
		if result:
			# Split the line into GID, alertID and message
			# (becomes generator[0], [1] and [2] respectively)
			generator = result.group(0).split(" || ")
			
			# Overwrite existing, or create new, generator:
			try:
				try:
					# TODO: Trenger vi except for MultipleObjectsReturned her? Streng tatt KAN det skje siden GID+alertID ikke er PRI?
					oldGenerator = Generator.objects.get(GID=generator[0], alertID=generator[1])
					oldGenerator.message = generator[2]
					oldGenerator.save()
				except Generator.DoesNotExist:
					Generator.objects.create(GID=generator[0], alertID=generator[1], message=generator[2])
			except IndexError:
				# If one or more indexes are invalid, the generator is badly formatted
				raise BadFormatError("Badly formatted generator")
			
	def parseFile(self, fn, path, **kwargs):
		def parse():
			"""Method for simple parsing of a file defined by path. 
			Every line is sent to the function defined by fn."""
			
			logger = logging.getLogger(__name__)
			logger.info("Parsing file "+path)
			
			try:		
				infile = open(path, "r")
			except IOError:
				logger.info("File '%s' not found, nothing to parse." % path)
				
			for i,line in enumerate(infile):
				try:
					fn(raw=line, **kwargs)
				except BadFormatError, e:
					# Log exception message, file name and line number
					logger.error("%s in file '%s', line " % (str(e), path, str(i+1)))
		return parse
				
class UpdateFile(models.Model):
	"""An Update comes with several files. Each of the files is represented by an UpdateFile object."""

	name = models.CharField(max_length=40)
	update = models.ForeignKey('Update', related_name="files")
	checksum = models.CharField(max_length=80)
	isParsed = models.BooleanField()
	
	def __repr__(self):
		return "<UpdateFile name:%s, update:%s-%s, md5:%s>" % (self.name, self.update.source.name, self.update.time, self.checksum)

	def __str__(self):
		return "<UpdateFile name:%s, update:%s-%s>" % (self.name, self.update.source.name, self.update.time)
