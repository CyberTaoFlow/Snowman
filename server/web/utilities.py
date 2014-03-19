#!/usr/bin/python

from core.models import Sensor

class UserSettings():
	DEFAULT = 0
	RULELIST = 1
	
	@staticmethod
	def getPageLength(request, pagetype = DEFAULT):
		return 20

def rulesToTemplate(ruleList):
	"""
	This method takes Django Query objects containing a list of rules. 
	
	It returns a list of objects that can be put directly into the template without any additional processing.
	"""
	
	# We get the count of all sensors in the system.
	sensorCount = Sensor.objects.count()
	
	# This list will be whats returned.
	chewedRules = []
	
	# We iterate over all the rules.
	for rule in ruleList:
		
		# We go get a number of variables.
		ruleID = rule.id
		ruleGID = rule.generator.GID
		ruleSID = rule.SID
		ruleThresholdCount = rule.thresholds.count()
		ruleSuppressCount = rule.suppress.count()
		ruleCurrentRevision = rule.getCurrentRevision()
		ruleRev = ruleCurrentRevision.rev
		ruleMsg = ruleCurrentRevision.msg
		ruleRaw = ruleCurrentRevision.raw
		ruleUpdateTime = ruleCurrentRevision.update.first().time
		ruleRuleSet = rule.ruleSet
		ruleRuleSetName = ruleRuleSet.name
		ruleClass = rule.ruleClass
		ruleClassName = ruleClass.classtype
		ruleClassPriority = ruleClass.priority
		ruleActive = rule.active
		
		# To save time in the template, we go get the reference fields here.
		chewedRuleReferences = []
		for reference in ruleCurrentRevision.references.all():
			chewedRuleReferences.append({'urlPrefix':reference.referenceType.urlPrefix, 'reference': reference.reference})
		
		# Based on the priority, a certain color is to be picked.
		if ruleClassPriority == 1:
			ruleClassPriorityColor = "btn-danger"
		elif ruleClassPriority == 2:
			ruleClassPriorityColor = "btn-warning"
		elif ruleClassPriority == 3:
			ruleClassPriorityColor = "btn-success"
		else:
			ruleClassPriorityColor = "btn-primary"
		
		# If the rule is active, we calculate how many sensors its active on.
		if (ruleActive):
			ruleActiveOnSensors = ruleRuleSet.sensors.values_list('name', flat=True)
			ruleActiveOnSensorsCount = ruleRuleSet.sensors.count()
			ruleInActiveOnSensorsCount = sensorCount - ruleActiveOnSensorsCount
		else: # If the rule isnt active, it wont be active on any sensors
			ruleActiveOnSensors = []
			ruleActiveOnSensorsCount = 0
			ruleInActiveOnSensorsCount = sensorCount
		
		# Finally we feed all the variables into an object and append it to the return list.
		chewedRules.append({'ruleID':ruleID,'ruleGID':ruleGID,'ruleSID':ruleSID,'ruleThresholdCount':ruleThresholdCount,
						'ruleSuppressCount':ruleSuppressCount,'ruleRev':ruleRev,'ruleMsg':ruleMsg,
						'ruleReferences':chewedRuleReferences,'ruleRaw':ruleRaw,
						'ruleUpdateTime':ruleUpdateTime,'ruleRuleSetName':ruleRuleSetName,'ruleClassName':ruleClassName,
						'ruleClassPriority':ruleClassPriority,'ruleActiveOnSensors':ruleActiveOnSensors,'ruleActiveOnSensorsCount':ruleActiveOnSensorsCount, 
						'ruleInActiveOnSensorsCount':ruleInActiveOnSensorsCount, 'ruleActive':ruleActive, 'ruleClassPriorityColor': ruleClassPriorityColor})
	
	
	# Once all rules are iterated over, we send the clean objects back.
	return chewedRules

def ruleSetsToTemplate(ruleSetList):
	"""
	This method takes Django Query objects containing a list of rulesets. 
	
	It returns a list of objects that can be put directly into the template without any additional processing.
	"""
	
	# We get the count of all sensors in the system.
	sensorCount = Sensor.objects.count()
	
	# This list will be whats returned.
	chewedRuleSets = []
	
	# We iterate over all the rulesets.
	for ruleSet in ruleSetList:
		
		# We go get a number of variables.
		ruleSetID = ruleSet.id
		ruleSetName = ruleSet.name
		ruleSetActive = ruleSet.active
		
		#TODO: comment this
		if ruleSet.childSets.count() > 0:
			ruleSetHasChildren = True
			
			ruleSetRulesCount = ruleSet.rules.count()
			if ruleSetRulesCount:
				ruleSetHasRules = 1
				ruleSetActiveRulesCount = ruleSet.rules.filter(active=True).count()
			else:
				ruleSetHasRules = False
				ruleSetActiveRulesCount = 0
			
			for child in ruleSet.childSets.all():
				ruleSetRulesCount += childRuleCount(child)
				ruleSetActiveRulesCount += childRuleActiveCount(child)
			
			ruleSetInActiveRulesCount = ruleSetRulesCount - ruleSetActiveRulesCount
		else:
			# We calculate the number of rules the ruleset has.
			ruleSetHasChildren = False
			ruleSetRulesCount = ruleSet.rules.count()
			if ruleSetRulesCount:
				ruleSetHasRules = True
			else:
				ruleSetHasRules = False
			ruleSetActiveRulesCount = ruleSet.rules.filter(active=True).count()
			ruleSetInActiveRulesCount = ruleSetRulesCount - ruleSetActiveRulesCount
		
		
		# If the ruleset is active, we calculate how many sensors its active on.
		if (ruleSetActive):
			ruleSetActiveOnSensors = ruleSet.sensors.values_list('name', flat=True)
			ruleSetActiveOnSensorsCount = ruleSet.sensors.count()
			ruleSetInActiveOnSensorsCount = sensorCount - ruleSetActiveOnSensorsCount
		else: # If the ruleset isnt active, it wont be active on any sensors
			ruleSetActiveOnSensors = []
			ruleSetActiveOnSensorsCount = 0
			ruleSetInActiveOnSensorsCount = sensorCount

		# Finally we feed all the variables into an object and append it to the return list.
		chewedRuleSets.append({'ruleSetID':ruleSetID,'ruleSetName':ruleSetName,'ruleSetRulesCount':ruleSetRulesCount,'ruleSetActiveRulesCount':ruleSetActiveRulesCount,
							'ruleSetInActiveRulesCount':ruleSetInActiveRulesCount,'ruleSetActiveOnSensors':ruleSetActiveOnSensors,'ruleSetActiveOnSensorsCount':ruleSetActiveOnSensorsCount,
							'ruleSetInActiveOnSensorsCount':ruleSetInActiveOnSensorsCount,'ruleSetActive':ruleSetActive, 'ruleSetHasChildren':ruleSetHasChildren,
							'ruleSetHasRules':ruleSetHasRules})
	
	
	# Once all rulesets are iterated over, we send the clean objects back.
	return chewedRuleSets

def ruleSetHierarchyListToTemplate(ruleSetList, level):
	
	# This list will be whats returned.
	chewedRuleSets = []
	
	# We iterate over all the rulesets.
	for ruleSet in ruleSetList:
		
		# We go get a number of variables.
		ruleSetID = ruleSet.id
		ruleSetName = ruleSet.name
		
		chewedRuleSets.append({'ruleSetID':ruleSetID,'ruleSetName':(" - "*level)+ruleSetName})
		
		if ruleSet.childSets.count() > 0:
			ruleSet.childSets.all()
			for item in ruleSetHierarchyListToTemplate(ruleSet.childSets.all(), level+1):
				chewedRuleSets.append(item)
	
	return chewedRuleSets

def ruleClassesToTemplate(ruleClassList):
	"""
	This method takes Django Query objects containing a list of rulesets. 
	
	It returns a list of objects that can be put directly into the template without any additional processing.
	"""
	
	# This list will be whats returned.
	chewedRuleClasses = []
	
	# We iterate over all the ruleclasses.
	for ruleClass in ruleClassList:
		
		# We go get a number of variables.
		ruleClassID = ruleClass.id
		ruleClassName = ruleClass.classtype
		ruleClassDescription = ruleClass.description
		
		# We calculate the number of rules the ruleclass has.
		ruleClassRulesCount = ruleClass.rules.count()
		ruleClassActiveRulesCount = ruleClass.rules.filter(active=True).count()
		ruleClassInActiveRulesCount = ruleClassRulesCount - ruleClassActiveRulesCount
		
		ruleClassPriority = ruleClass.priority
		
		# Based on the priority, a certain color is to be picked.
		if ruleClassPriority == 1:
			ruleClassPriorityColor = "btn-danger"
		elif ruleClassPriority == 2:
			ruleClassPriorityColor = "btn-warning"
		elif ruleClassPriority == 3:
			ruleClassPriorityColor = "btn-success"
		else:
			ruleClassPriorityColor = "btn-primary"


		# Finally we feed all the variables into an object and append it to the return list.
		chewedRuleClasses.append({'ruleClassID':ruleClassID,'ruleClassName':ruleClassName,'ruleClassRulesCount':ruleClassRulesCount,'ruleClassActiveRulesCount':ruleClassActiveRulesCount,
							'ruleClassInActiveRulesCount':ruleClassInActiveRulesCount,'ruleClassPriorityColor':ruleClassPriorityColor,'ruleClassDescription':ruleClassDescription,
							'ruleClassPriority':ruleClassPriority})

	# Once all ruleclasses are iterated over, we send the clean objects back.
	return chewedRuleClasses

#TODO: comment this
def childRuleCount(ruleSet):
	
	ruleSetRulesCount = ruleSet.rules.count()
	
	if ruleSet.childSets:
		for child in ruleSet.childSets.all():
			ruleSetRulesCount += childRuleCount(child)
	
	return ruleSetRulesCount

#TODO: comment this
def childRuleActiveCount(ruleSet):
	ruleSetActiveRulesCount = ruleSet.rules.filter(active=True).count()
	
	if ruleSet.childSets:
		for child in ruleSet.childSets.all():
			ruleSetActiveRulesCount += childRuleActiveCount(child)
			
	return ruleSetActiveRulesCount