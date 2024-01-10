import time

import os
import sys


def is_node_ready(w3):
    try:
        w3.zksync.get_block_number()
        return True
    except Exception as _:
        return False


def wait_for_node():
    print("Waiting for node to be ready")
    from zksync2.module.module_builder import ZkSyncBuilder

    max_attempts = 30
    w3 = ZkSyncBuilder.build("http://localhost:3050")

    for i in range(max_attempts):
        if is_node_ready(w3):
            print("Node is ready")
            return
        time.sleep(20)
    raise Exception("Maximum retries exceeded.")


if __name__ == '__main__':
    current_directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.join(current_directory, '..')
    sys.path.append(parent_directory)
    try:
        wait_for_node()
    except Exception as e:
        print(f"Error: {e}")
    sys.path.remove(parent_directory)
