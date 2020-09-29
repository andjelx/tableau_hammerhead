import os
import shutil


#=== manual notes for copy from internal hammerhead===
#STEP 1 - copy these folders from _git/hammerhead/
 # - src/install_on_linux
 # - src/install_on_windows
 # - src/include, except cyberark_certchain.pem
 # - src/*,py   except createdesktop.py, copyinstaller_internal.py, customrestore_instance.py, modifyinstance.py, reportinstance.py, shareAmiWithOtherAccounts.py, upgradeinstance.py
#STEP 2 - copy files from src/cli/override over their corresponding .py files
#STEP 3 - individual modifications
  # remove copy setupserver.jar references from windows and linux scripts
     #tsm-install-node1.sh line 19, tsm-install-node1.ps1 line 31.


#TODO: tsm_version break into two?

'''
def removeLines(rootdir, fname, remove_line):
    fname = os.path.abspath(os.path.join(rootdir, fname))
    f = open(fname)
    output = []
    for line in f:
        line2 = line.rstrip()
        if not line2.endswith(remove_line):
            output.append(line)
        else:
            print(f"removing line from file: '{fname}' remove: '{remove_line}'")
    f.close()
    f = open(fname, 'w')
    f.writelines(output)
    f.close()


def run():
    """ copy src directory except for certain subdirectories. remove certain lines of code  """
    root_src_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../_git/hammerhead/src"))
    root_dst_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../src"))
    print("\n\nSTEP copy Hammerhead source code to github")
    print(f"Source: {root_src_dir}")
    print(f"Dest: {root_dst_dir}")
    print()

    #STEP - initialize ignoreDirnames
    ignoreDirnames = ['config', '__pycache__', 'install_on_windows\\user-scripts', 'install_on_linux\\user-scripts', 'hammerdeploy', 'cli']
    ignoreFilenames = []
    # ["nessusagent.py", "reportinstance.py", "domainjoin.py", "shareAmiWithOtherAccounts.py"
    #                    "hammerdal.py", "slackutil.py", "teamcityutil.py", "tsm_version.py"]
    for i in range(0, len(ignoreDirnames)):
        ignoreDirnames[i] = os.path.join(root_src_dir, ignoreDirnames[i])  # convert to absolute path

    #STEP - do copy
    for src_dir, dirs, files in os.walk(root_src_dir):
        found=False
        for ig in ignoreDirnames:
            if src_dir.startswith(ig):
                print(f"skip dir {src_dir}")
                found=True
                break
        if found:
            continue

        dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        print(f"copy files to dir {dst_dir}")
        for filename in files:
            if filename in ignoreFilenames:
                print(f"skip file {filename}")
                continue
            src_file = os.path.join(src_dir, filename)
            dst_file = os.path.join(dst_dir, filename)
            if os.path.exists(dst_file):
                os.remove(dst_file)
            shutil.copy(src_file, dst_dir)

    #STEP - remove lines
    print()
    hcliExclude = '#HCLI exclude'
    remove_stuff = [("createinstance.py", hcliExclude)]
    for re in remove_stuff:
        removeLines(root_dst_dir, re[0], re[1])




if __name__ == '__main__':
    run()

'''

