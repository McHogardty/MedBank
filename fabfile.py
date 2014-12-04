from fabric.api import *

REMOTE_NAME = "prod"
REMOTE_URL = "sydneym2@sydneymedsoc.org.au"
REMOTE_DIRECTORY = "/home4/sydneym2/repo/medbank"
PRODUCTION_DIRECTORY = "/home4/sydneym2/django_sites/medbank"
WSGI_FILE = "mysite.fcgi"
WSGI_LOCATION = "/home4/sydneym2/public_html/medbank/%s" % WSGI_FILE

env.hosts = [REMOTE_URL, ]

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
			run('rsync -r --delete ./ %s --exclude ".git*" --exclude "local_settings.py"' % PRODUCTION_DIRECTORY)

	with cd(PRODUCTION_DIRECTORY):
		with hide("stderr", "stdout"):
			run('python manage.py migrate')
			run('python manage.py collectstatic --noinput')
			run('find . -name "*.pyc" -exec rm -f {} \;')
			run('touch %s' % WSGI_LOCATION)
			run('killall %s' % WSGI_FILE)