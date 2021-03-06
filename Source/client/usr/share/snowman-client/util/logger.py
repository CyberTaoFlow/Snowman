#!/usr/bin/python
import logging

from util.config import Config


def initialize():
	messages = []
	levels = {'NOTSET': logging.NOTSET, 'DEBUG': logging.DEBUG, 'INFO': logging.INFO, 'WARNING': logging.WARNING, 'ERROR': logging.ERROR, 'CRITICAL': logging.CRITICAL}
	loglevel = Config.get("logging", "severity")
	logfile = Config.get("logging", "logfile")

	# If the configfile lists a loglevel that is not valid, assume info.
	if(loglevel not in levels):
		# Since the logger is not yet initialized, add the logging-message to the messagelist, so that we can
		#   log it whenever the logger is initialized.
		messages.append(("LogLevel is not correctly set in the config-file. Assuming INFO", logging.ERROR))
		print "A"
		loglevel = "INFO"
	
	rootlogger = logging.getLogger()
	formatter = logging.Formatter('%(asctime)s: %(name)s: %(levelname)s - %(message)s')
	
	fh = logging.FileHandler(logfile)
	fh.setFormatter(formatter)
	rootlogger.addHandler(fh)
	rootlogger.setLevel(levels[loglevel])
	
	messages.append(("Logger initialized", logging.INFO))
		
	# Now that the logger is initialized, log the messages that appared during the initialization of the module 
	logger = logging.getLogger(__name__)
	for m in messages:
		logger.log(m[1], m[0])
