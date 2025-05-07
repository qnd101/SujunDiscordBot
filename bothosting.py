import os
import subprocess
import time
import pwd

class HostingManger:
    def __init__(self, rootdir, initscriptpath):
        self.rootdir = os.path.abspath(rootdir)
        self.initscriptpath = initscriptpath
        self.procs = {}
        self.proctimeout = 5

    # add user for each folder under rootdir
    def initialize(self):
        for entry in os.scandir(self.rootdir):
            if entry.is_dir():
                subprocess.run(["useradd", "-d", entry.path, entry.name])
                subprocess.run(["chown", "-R", f"{entry.name}:{entry.name}", entry.path])

    def user_dir(self, uid) -> str:
        return os.path.join(self.rootdir, str(uid))

    def user_exists(self, uid) -> bool:
        for entry in os.scandir(self.rootdir):
            if entry.is_dir() and entry.name == str(uid):
                return True
        return False

    # create folder if there is none and does initializing task
    # if there is no user create one
    def init_user(self, uid):
        subprocess.run([self.initscriptpath, self.user_dir(uid),str(uid)])

    # prints all dirs, then all files
    def get_subobjs(self, uid) -> tuple[list[str], list[str]]:
        path = os.path.join(self.rootdir, str(uid))
        dirs = [entry.name for entry in os.scandir(path) if entry.is_dir()]
        files = [entry.name for entry in os.scandir(path) if entry.is_file()]
        return dirs, files
    
    def bot_isrunning(self, uid):
        return (uid in self.procs) and self.procs[uid].poll() == None

    def bot_run(self, uid):
        if self.bot_isrunning(uid):
            return
        wd = self.user_dir(uid)
        self.procs[uid] = subprocess.Popen(
            ["su", "-", str(uid), "-c", "./startup.sh"], cwd=wd
        )
    
    # try graceful termination -> kill process after timeout
    def bot_stop(self, uid):
        if not self.bot_isrunning(uid):
            return
        pw_uid = pwd.getpwnam(str(uid)).pw_uid
        self.procs[uid].terminate()  # Send Sigterm to the process
        # self.procs[uid].wait() # Wait for the process to terminate
        subprocess.run(["pkill", "-u", str(pw_uid)]) # Send Sigterm to child processes (exactly, all process owned by the user)
        start_time = time.time()
        while time.time() - start_time < self.proctimeout:
            if subprocess.run(['pgrep', '-u', str(pw_uid)]).returncode != 0:  # Check if any process of user is running
                print(f"Bot of {uid} terminated gracefully.")
                return
            time.sleep(0.5) 
        
        subprocess.run(["pkill","-9", "-u", str(pw_uid)]) # Send Sigkill to all processes owned by the user
        print(f"Bot of {uid} was killed after timeout.")

    def chown_item(self, uid, item):
        path = os.path.join(self.user_dir(uid), item)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Path not found: {path}")
        if os.path.isdir(path):
            subprocess.run(["chown", "-R", f"{uid}:{uid}", path])
            subprocess.run(["chmod", "-R", "770", path])
        else:
            subprocess.run(["chown", f"{uid}:{uid}", path])
            subprocess.run(["chmod", "770", path])