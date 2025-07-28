import ctypes
import platform

if platform.system() == "Windows":
    # On Windows, load the .dll file
    library_path = "./mc_manager.dll"
elif platform.system() == "Linux":
    # On Linux, load the .so file
    library_path = "./libmc_manager.so"
else:
    raise Exception("unsupported os")

mc_manager = ctypes.CDLL(library_path)

class ChatDataC(ctypes.Structure):
    _fields_ = [
        ("player", ctypes.POINTER(ctypes.c_char)),
        ("msg", ctypes.POINTER(ctypes.c_char)),
    ]

# Define the MCSrvC struct, which holds a pointer to MCSrv
class MCSrvC(ctypes.Structure):
    _fields_ = [
        ("_0", ctypes.POINTER(ctypes.c_void_p)),  # Pointer to MCSrv
    ]

# Function signatures
mc_manager.MCSrvC_new.restype = MCSrvC
mc_manager.MCSrvC_new.argtypes = [
    ctypes.c_longlong,  # pause_time_minutes
    ctypes.c_longlong,  # cool_time_minutes
    ctypes.POINTER(ctypes.c_char),  # start_script_path
    ctypes.POINTER(ctypes.c_char),  # backup_script_path
]

mc_manager.MCSrvC_update.restype = None
mc_manager.MCSrvC_update.argtypes = [MCSrvC]

mc_manager.MCSrvC_stop.restype = ctypes.c_int
mc_manager.MCSrvC_stop.argtypes = [MCSrvC]

mc_manager.MCSrvC_start.restype = ctypes.c_int
mc_manager.MCSrvC_start.argtypes = [MCSrvC]

mc_manager.MCSrvC_try_pop_chat.restype = ctypes.POINTER(ChatDataC)
mc_manager.MCSrvC_try_pop_chat.argtypes = [MCSrvC]

mc_manager.MCSrvC_status.restype = ctypes.POINTER(ctypes.c_char)
mc_manager.MCSrvC_status.argtypes = [MCSrvC]

mc_manager.MCSrvC_status_free.restype = None
mc_manager.MCSrvC_status_free.argtypes = [ctypes.POINTER(ctypes.c_char)]

mc_manager.MCSrvC_try_pop_chat_free.restype = None
mc_manager.MCSrvC_try_pop_chat_free.argtypes = [ctypes.POINTER(ChatDataC)]

mc_manager.MCSrvC_extern_chat.restype = ctypes.c_int
mc_manager.MCSrvC_extern_chat.argtypes = [MCSrvC, ctypes.POINTER(ctypes.c_char), ctypes.POINTER(ctypes.c_char)]

mc_manager.MCSrvC_new_free.restype = None
mc_manager.MCSrvC_new_free.argtypes = [MCSrvC]

# a python wrapper for mc_manager.MCSrvC_try_pop_chat
def try_pop_chat(mcsrv: MCSrvC):
    try:
        chat_data_ptr = mc_manager.MCSrvC_try_pop_chat(mcsrv)
        if chat_data_ptr:
            # Dereference the pointer to get the ChatDataC structure
            chat_data = chat_data_ptr.contents
            
            # Convert the C-style strings (char*) to Python strings
            player = ctypes.cast(chat_data.player, ctypes.c_char_p).value.decode('utf-8') if chat_data.player else None
            msg = ctypes.cast(chat_data.msg, ctypes.c_char_p).value.decode('utf-8') if chat_data.msg else None
            
            mc_manager.MCSrvC_try_pop_chat_free(chat_data_ptr)

            return player, msg    
        return None, None
    except Exception as e:
        print(e)
        return None, None

def get_status(mcsrv: MCSrvC):
    try:
        desc_raw = mc_manager.MCSrvC_status(mcsrv)
        if desc_raw:
            desc = ctypes.cast(desc_raw, ctypes.c_char_p).value.decode('utf-8')
            mc_manager.MCSrvC_status_free(desc_raw)
            return desc
        return None
    except Exception as e:
        print(e)
        return None
    
def update(mcsrv: MCSrvC):
    try:
        mc_manager.MCSrvC_update(mcsrv)
    except Exception as e:
        print(f"{e}")

def start(mcsrv: MCSrvC):
    try:
        return mc_manager.MCSrvC_start(mcsrv)
    except Exception as e:
        print(e)


def stop(mcsrv: MCSrvC):
    try:
        result = mc_manager.MCSrvC_stop(mcsrv)
        if result == 0:
            return True  # Success
        else:
            return False  # Failure
    except Exception as e:
        print(e)

def extern_chat(mcsrv: MCSrvC, player: str, msg: str):
    try:
        if mc_manager.MCSrvC_extern_chat(mcsrv, player.encode('utf-8'), msg.encode('utf-8')) == 0:
            return True
        return False
    except Exception as e:
        print(e)

    
def new(pause_time_minutes, cool_time_minutes, start_script_path, backup_script_path):
    # Convert strings to bytes (as C expects UTF-8 encoded bytes)
    start_script_path_bytes = start_script_path.encode('utf-8')
    backup_script_path_bytes = backup_script_path.encode('utf-8')

    try:
    # Call the C function to create a new MCSrvC instance
        mcsrv = mc_manager.MCSrvC_new(
            pause_time_minutes,
            cool_time_minutes,
            start_script_path_bytes,
            backup_script_path_bytes
        )

        return mcsrv
    except Exception as e:
        print(e)

def free(mcsrv: MCSrvC):
    # Call the C function to free the MCSrvC instance
    try: 
        mc_manager.MCSrvC_new_free(mcsrv)
    except Exception as e:
        print(e)
