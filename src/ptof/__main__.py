import sys, os

if __name__ == '__main__':
   sys.path.append(os.getcwd())


from ptof.cli import cli

# 主程序
cli()
