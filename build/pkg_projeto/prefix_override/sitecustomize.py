import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/evelyn/trainee/Projeto-Final-Eletronica-Grupos-1e4/install/pkg_projeto'
