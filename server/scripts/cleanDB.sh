#!/bin/bash

URL="http://192.168.6.11/static/rules/"

FILE=("testset.1-1.tar.gz" "testset.10-1.tar.gz" "testset.100-10.tar.gz" "testset.1000-1.tar.gz" "testset.1000-100.tar.gz" "testset.10000-1000.tar.gz" "testset.inactive.100-10.tar.gz" "s.tar.gz" "testset.inactive.100-10.tar.gz")

FILE2=("testset.rev2.100-10.tar.gz" "testset.rev3.100-10.tar.gz")

FILE3=("s.1.tar.gz" "s.2.tar.gz")

function runTest {

	echo "DROP DATABASE srm; CREATE DATABASE srm;" | mysql -usrm -pbah5oofa6booyeeJa2Da 
	../manage.py syncdb --noinput
	python createDemoData.py

	echo "INSERT INTO update_source (name, url, md5url, schedule, locked) VALUES ('Testing', '$URL$1', '$URL$1.md5', 'No automatic updates', 0);"  | mysql -usrm -pbah5oofa6booyeeJa2Da srm

	python runTimedUpdate.py 3

}

function runSpecialTest {

	echo "DROP DATABASE srm; CREATE DATABASE srm;" | mysql -usrm -pbah5oofa6booyeeJa2Da 
	../manage.py syncdb --noinput
	python createDemoData.py

	echo "INSERT INTO update_source (name, url, md5url, schedule, locked) VALUES ('Testing', '$URL$1', '$URL$1.md5', 'No automatic updates', 0);"  | mysql -usrm -pbah5oofa6booyeeJa2Da srm

	python runTimedUpdate.py 3

	echo "UPDATE update_source SET url = '$URL$2', md5url = '$URL$2.md5' WHERE id=3;"  | mysql -usrm -pbah5oofa6booyeeJa2Da srm

	python runTimedUpdate.py 3

}

for file in ${FILE[*]}
do
	echo -e "$file" >> /tmp/srm-update-timing.txt
	for i in {1..5}
	do
		runTest $file
	done
	echo -e "\n" >> /tmp/srm-update-timing.txt
done

for i in {1..5}
do
	runSpecialTest FILE2[0] FILE2[1]
done

for i in {1..5}
do
	runSpecialTest FILE3[0] FILE3[1]
done


