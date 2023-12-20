#!/bin/bash
#set -e
##################################################################################################################
# Author    : Erik Dubois
# Website   : https://www.erikdubois.be
# Website   : https://www.alci.online
# Website   : https://www.ariser.eu
# Website   : https://www.arcolinux.info
# Website   : https://www.arcolinux.com
# Website   : https://www.arcolinuxd.com
# Website   : https://www.arcolinuxb.com
# Website   : https://www.arcolinuxiso.com
# Website   : https://www.arcolinuxforum.com
##################################################################################################################
#
#   DO NOT JUST RUN THIS. EXAMINE AND JUDGE. RUN AT YOUR OWN RISK.
#
##################################################################################################################
#tput setaf 0 = black
#tput setaf 1 = red
#tput setaf 2 = green
#tput setaf 3 = yellow
#tput setaf 4 = dark blue
#tput setaf 5 = purple
#tput setaf 6 = cyan
#tput setaf 7 = gray
#tput setaf 8 = light blue
##################################################################################################################

# reset - commit your changes or stash them before you merge
# git reset --hard - personal alias - grh

workdir=$(pwd)

# checking if I have the latest files from github
echo "Checking for newer files online first"
git pull
if [ -d /home/erik/ARCO/ARCOLINUX/sofirem/usr/share/sofirem/__pycache__/ ]; then
	sudo rm -rv /home/erik/ARCO/ARCOLINUX/sofirem/usr/share/sofirem/__pycache__/
fi

if [ -f /home/erik/ARCO/ARCOLINUX/sofirem/usr/share/sofirem/cache/installed.lst ]; then
	sudo rm -v /home/erik/ARCO/ARCOLINUX/sofirem/usr/share/sofirem/cache/installed.lst
fi

if [ -f /home/erik/ARCO/ARCOLINUX/sofirem/usr/share/sofirem/cache/installed.lst ]; then
	sudo rm -v //home/erik/ARCO/ARCOLINUX/sofirem/usr/share/sofirem/cache/yaml-packages.lst
fi

echo "getting ASA script"
wget https://raw.githubusercontent.com/arcolinux/arcolinux-spices/master/usr/share/arcolinux-spices/scripts/get-the-keys-and-repos.sh -O $workdir/usr/share/sofirem/scripts/get-the-keys-and-repos.sh
chmod +x $workdir/usr/share/sofirem/scripts/get-the-keys-and-repos.sh

echo "Keyring from ArcoLinux"
rm -v /home/erik/ARCO/ARCOLINUX/sofirem/usr/share/sofirem/packages/arcolinux-keyring/*
cp -v /home/erik/ARCO/ARCOLINUX-REPO/arcolinux_repo/x86_64/arcolinux-keyring*pkg.tar.zst /home/erik/ARCO/ARCOLINUX/sofirem/usr/share/sofirem/packages/arcolinux-keyring/

echo "Mirror from ArcoLinux"
rm -v /home/erik/ARCO/ARCOLINUX/sofirem/usr/share/sofirem/packages/arcolinux-mirrorlist/*
cp -v /home/erik/ARCO/ARCOLINUX-REPO/arcolinux_repo/x86_64/arcolinux-mirror*pkg.tar.zst /home/erik/ARCO/ARCOLINUX/sofirem/usr/share/sofirem/packages/arcolinux-mirrorlist/

# Below command will backup everything inside the project folder
git add --all .

# Give a comment to the commit if you want
echo "####################################"
echo "Write your commit comment!"
echo "####################################"

read input

# Committing to the local repository with a message containing the time details and commit text

git commit -m "$input"

# Push the local files to github

if grep -q main .git/config; then
	echo "Using main"
		git push -u origin main
fi

if grep -q master .git/config; then
	echo "Using master"
		git push -u origin master
fi

echo "################################################################"
echo "###################    Git Push Done      ######################"
echo "################################################################"
