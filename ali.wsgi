import sys
import os
#import pwd
path =  '/home/aliscraper/aliscraper'
sys.path.insert(0, path)
os.chdir(path)

#print('mod_wsgi.process_group', environ['mod_wsgi.process_group'])
#print('user', pwd.getpwuid(os.getuid()))


from webapp import app as application

