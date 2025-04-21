import os
import subprocess
import time

class HostingManger:
    def __init__(self, rootdir, initscriptpath):
        self.rootdir = os.path.abspath(rootdir)
        self.initscriptpath = initscriptpath
        self.procs = {}
        self.proctimeout = 3

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
        self.procs[uid].terminate()
        start_time = time.time()
        while time.time() - start_time < self.proctimeout:
            if self.procs[uid].poll() is not None:  # Check if the process is finished
                return
            time.sleep(0.1) 
        self.procs[uid].kill()
        self.procs[uid].wait()