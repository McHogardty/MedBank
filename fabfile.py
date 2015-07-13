from fabric.api import *

REMOTE_NAME = "prod"
REMOTE_URL = "webmaster@128.199.65.180"
REMOTE_DIRECTORY = "/home/webmaster/repo/medbank"
PRODUCTION_DIRECTORY = "/var/www/medbank"
KEY_FILE = "/Users/michael/.ssh/sums-webmaster-rsa"
# WSGI_FILE = "mysite.fcgi"
WSGI_LOCATION = "%s/medbank/wsgi.py" % PRODUCTION_DIRECTORY

env.hosts = [REMOTE_URL, ]
env.key_filename = '/Users/michael/.ssh/sums-webmaster-rsa'

def sync():
	# Check first that we have a production location to push to. If not, add one.
	with hide("running"): 
		result = local("git remote", capture=True).split("\n")
	if REMOTE_NAME not in result:
		local("git remote add %s %s:%s" % (REMOTE_NAME, REMOTE_URL, REMOTE_DIRECTORY))

	# Push to the production server.
	with hide("stderr", "stdout"):
		local("git push %s master:v1" % REMOTE_NAME)


def deploy():
	# First, sync the files with the production server.
	sync()

	with cd(REMOTE_DIRECTORY):
		with hide("stderr", "stdout"):
			run("git merge v1")
			run('rsync -r --delete ./ %s --exclude ".git*" --exclude "local_settings.py" --chown webmaster:www' % PRODUCTION_DIRECTORY)

	with cd(PRODUCTION_DIRECTORY):
		with hide("stderr", "stdout"):
			run('python manage.py migrate')
			run('python manage.py collectstatic --noinput')
			run('find . -name "*.pyc" -exec rm -f {} \;')
			run('touch %s' % WSGI_LOCATION)
	# 		run('killall %s' % WSGI_FILE)