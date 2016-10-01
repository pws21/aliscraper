import sys
import os
#import pwd
cwd = os.path.dirname(os.path.abspath(__file__))
src_path =  os.path.join(cwd, 'src')
sys.path.insert(0, src_path)
os.chdir(path)

#print('mod_wsgi.process_group', environ['mod_wsgi.process_group'])
#print('user', pwd.getpwuid(os.getuid()))


from webapp import app as application

