#!/usr/bin/env python
"""
"""

import datetime
import hashlib
import logging
import os
import resource
import sys
import traceback
import urllib2

# Add the parent folder of the script to the path
scriptpath = os.path.realpath(__file__)
scriptdir = os.path.dirname(scriptpath)
parentdir = os.path.dirname(scriptdir)
sys.path.append(parentdir)

from util.tools import doubleFork
doubleFork()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "srm.settings")

from update.models import Update, Source, UpdateLog
from update.tasks import UpdateTasks
from util.config import Config
import util.logger

logger = logging.getLogger(__name__)

if __name__ == "__main__":
	logger = logging.getLogger(__name__)
	
	# Grab the parametres.
	try:
		sourceID = int(sys.argv[1])
	except IndexError:
		print "Usage: %s <source_id>"
		sys.exit(1)

	try:
		source = Source.objects.get(pk=sourceID)
	except Source.DoesNotExist:
		logger.error("Could not find source with ID:%d" % sourceID)
		sys.exit(1)
	
	update = Update.objects.create(source=source, time=datetime.datetime.now())

	if(source.locked):
		logger.info("Could not update '%s', as there seems to already be an update going for this source.")
		sys.exit(1)
	else:
		source.locked = True
		source.save()
		logger.info("Starting the update from %s, with PID:%d." % (source.name, os.getpid()))
	
	if(source.md5url and len(source.md5url) > 0):
		UpdateLog.objects.create(update=update, time=datetime.datetime.now(), logType=UpdateLog.PROGRESS, text="1 Trying to fetch md5sum, to compare with last processed file.")
		try:
			socket = urllib2.urlopen(source.md5url)
			md5 = socket.read()
			md5 = md5.strip()
			socket.close()

			logger.debug("Downloaded-MD5:'%s'" % str(md5))
			logger.debug("LastUpdate-MD5:'%s'" % str(source.lastMd5))
		except:
			logger.warning("Could not find the md5-file at %s. Proceeding to download the main update-file." % source.md5url)
			md5 = ""
	else:
		logger.info("No md5-url file found. Proceeding to download the main update-file.")
		md5 = ""
	
	
	if(len(str(md5)) == 0 or str(md5) != str(source.lastMd5)):
		UpdateLog.objects.create(update=update, time=datetime.datetime.now(), logType=UpdateLog.PROGRESS, text="2 Downloading ruleset from source.")
		logger.info("Starting to download %s" % source.url)
		storagelocation = Config.get("storage", "inputFiles")		
		filename = storagelocation + source.url.split("/")[-1]
		
		if(os.path.isdir(storagelocation) == False):
			os.makedirs(storagelocation)

		try:
			socket = urllib2.urlopen(source.url)
	
			f = open(filename, "w")
			_hash = hashlib.md5()
			blocksize = 65536
			while True:
				buffer = socket.read(blocksize)
				if not buffer:
					socket.close()
					f.close()
					break
				f.write(buffer)
				_hash.update(buffer)

		except urllib2.HTTPError as e:
			UpdateLog.objects.create(update=update, time=datetime.datetime.now(), logType=UpdateLog.PROGRESS, text="100 Error during downloading. Check log for details..")
			logger.error("Error during download: %s" % str(e))
			source.locked = False
			source.save()
			sys.exit(1)

		logger.debug("Downloaded-MD5:'%s'" % str(_hash.hexdigest()))
		logger.debug("LastUpdate-MD5:'%s'" % str(source.lastMd5))
	
		if(str(_hash.hexdigest()) != str(source.lastMd5)):
			UpdateLog.objects.create(update=update, time=datetime.datetime.now(), logType=UpdateLog.PROGRESS, text="7 Starting to process the download.")
			logger.info("Processing the download" )
			try:
				UpdateTasks.runUpdate(filename, source.name, update=update)
			except Exception as e:
				logger.critical("Hit exception while running update: %s" % str(e))
				UpdateLog.objects.create(update=update, time=datetime.datetime.now(), logType=UpdateLog.PROGRESS, text="100 ERROR: Hit an exception while processing the update.")
				logger.debug("%s" % (traceback.format_exc()))
				source.locked = False
				source.save()
				sys.exit(1)
		
			logger.info("Storing md5 of this update: %s" % (_hash.hexdigest()))
			source.lastMd5 = _hash.hexdigest()
			source.save()
		else:
			logger.info("The downloaded file has the same md5sum as the last file we updated from. Skipping update.")
			UpdateLog.objects.create(update=update, time=datetime.datetime.now(), logType=UpdateLog.PROGRESS, text="100 Downloaded file is processed earlier. Finishing.")
	else:
		logger.info("We already have the latest version of the %s ruleset. Skipping download." % source.name)
		UpdateLog.objects.create(update=update, time=datetime.datetime.now(), logType=UpdateLog.PROGRESS, text="100 MD5 sum mathces last update. Skipping.")

	logger.info("Finished the update, with PID:%d, from: %s" % (os.getpid(), source.name))
	UpdateLog.objects.create(update=update, time=datetime.datetime.now(), logType=UpdateLog.PROGRESS, text="100 Finished the update.")
	source.locked = False
	source.save()
	
	if(update.ruleRevisions.count() == 0):
		update.delete()
