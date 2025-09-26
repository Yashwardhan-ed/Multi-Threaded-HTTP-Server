import socket
import concurrent.futures
import os
import sys
import time
import threading
from urllib.parse import unquote


interface = "127.0.0.1"
port = 8080
resources = "resources"
client_que = []
clients = 0
lock = threading.Lock()

def start_server(port, interface, resource_dir, maxPoolSize=10):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((interface, port))
    sock.listen()
    with concurrent.futures.ThreadPoolExecutor(max_workers=maxPoolSize) as executor:
        conn, addr = sock.accept()
        no_of_clients+=1
        executor.submit(handle_client_connection, conn, addr, executor, resource_dir)
    if clients >= maxPoolSize:
        print("Thread pool saturated, queing connection")
        client_que.append((conn, addr))



def handle_client_connection(conn, addr, executor, resources_dir):
    client_ip, client_port = addr
    print(f"Connection from {client_ip} {client_port}")
    try: 
        while True:
            raw_data = conn.recv(8192).decode("utf-8")
            if not raw_data:
                break
            request_lines = raw_data.splitlines()
            if len(request_lines) == 0:
                response = make_response(400, "Bad Request", error_page("400", "Bad Request", "Request Empty"))
                conn.sendall(response)
                print(" --> 400 Bad Request")
                return
            request_line = request_lines[0].strip()
            parts = request_line.split(" ")
            if len(parts) != 3: 
                response = make_response(400, "Bad Request", error_page("400", "Bad Request", "Malformed Request"))
                conn.sendall(response)
                print(" --> 400 Bad Request")
                return
            method, path, version = parts
            if version not in ("HTTP/1.1", "HTTP/1.0"):
                response = make_response(505, "Version not Supported", error_page("505", "Version not supported", "Wrong HTTP version"))
                conn.sendall(response)
                print(" --> 505 Version not supported")
            # resolve the path 
            ok, error_or_path = resolve_path(resource_dir, path)
            if ok == False:
                status_code = error_or_path.split(" ")[0]
                response = ""
                if status_code == "403":
                    response = make_response(status_code, "Forbidden", error_page(status_code, "Forbidden", "Forbidden Path"))
                else:
                    response = make_response(status_code, "Bad Request", error_page(status_code, "Bad Request", "Malformed Request"))
                conn.sendall(response)
                print(f" --> {error_or_path}")
                return
            # if method.upper() == "GET":

            # if method.upper() == "POST":
    except:
        response = make_response(500, "Internal Server Error", "Internal Server Error")
        conn.sendall(response)
        print(" --> 500 Internal Server Error")
        return
    finally:
        lock.acquire()
        no_of_clients-=1
        if not client_que.empty():
            client = client_que.pop()
            next_conn, next_addr = client
            executor.submit(handle_client_connection, next_conn, next_addr, executor)
        lock.release()

            
def resolve_path(resource_dir, request_path):
    path = request_path.split('?')[0] # separate path from query
    path = path.unquote() # remove any special characters if they exist in the path
    if path == "": # default empty path to /
        path = "/"
    if path == "/": # default / to /index.html page
        path == "/index.html"
    
    # avoid using absolute paths (security risk)
    if path.startswith('http://') or path.startswith('https://'):
        return False, "400 Malformed Request path"
    
    requested_rel = path.lstrip() # remove any leading /
    candidate_path = os.path.join(resource_dir, requested_rel) 
    real_path = os.path.realpath(resource_dir)
    real_prefix = real_path + os.path.sep

    if not candidate_path.startswith(real_prefix):
        return False, "403 Forbidden"
    return True, "200 Ok"

def make_response(status_code, reason, body_html, connection, extra_headers=None):
    if body_html == "":
        body = b""
    if isinstance(body_html, str):
        body = body_html.encode("utf-8")
    else:
        body = body_html
    headers = [
        f"HTTP/1.1 {status_code} {reason}",
        "Content-Type: text/html; charset=utf-8",
        f"Content-Length: [{len(body)}]",
        f"Date: [{time.gmtime()}]",
        "Server: Multi-threaded HTTP Server",
        f"Connection: {connection}"
    ]
    if extra_headers:
        header_blob = "\r\n".join(headers.extend(extra_headers)) + "\r\n\r\n"
    return header_blob.encode("utf-8") + body

def error_page(status_code, reason, detail):
    return f'''
            <html>
                <head>
                    <title>{status_code} {reason}</title>
                </head>
                <body>
                    <p>{detail}</p>
                </body>
            </html>
            '''

if __name__ == "__main__":
    PORT = port
    INTERFACE = interface
    threadpool_size = 10
    # sys.argv takes input from command line
    # sys.argv[0] is reserved for file name (e.g. server.py)
    if len(sys.argv) >= 2:
        try:
            PORT = int(sys.argv[1])
        except:
            print(f"Invalid port Number. Using Default {PORT}")
        if len(sys.argv) >= 3:
            INTERFACE = int(sys.argv[2])
        if len(sys.argv) >= 4:
            threadpool_size = int(sys.argv[3])
    
    base_dir = os.path.dirname(os.path.realpath(__file__))
    resource_dir = os.path.join(base_dir, resources)

    start_server(PORT, INTERFACE, resource_dir, threadpool_size)