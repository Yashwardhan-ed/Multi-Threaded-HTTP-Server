import socket
import concurrent.futures
import os
from collections import deque
import time
import sys
import json
from email.utils import formatdate
import threading
from urllib.parse import unquote


interface = "127.0.0.1"
port = 8080
resources = "resources"
client_que = deque()
no_of_clients = 0
# a lock is needed for maintaining client_que
lock = threading.Lock() 

def start_server(port, interface, resource_dir, maxPoolSize=10):
    global no_of_clients
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((interface, port))
    sock.listen()
    with concurrent.futures.ThreadPoolExecutor(max_workers=maxPoolSize) as executor:
        # start accepting client connections
        while True:
            conn, addr = sock.accept()
            # set timeout for connection
            conn.settimeout(30)
            # acquire a lock for no_of_clients
            lock.acquire()
            no_of_clients+=1
            # que connections if no of clients exceed pool size
            if no_of_clients >= maxPoolSize:
                print("Thread pool saturated, queing connection")
                client_que.append((conn, addr))
            else:
                executor.submit(handle_client_connection, conn, addr, executor, resource_dir)
            lock.release()



def handle_client_connection(conn, addr, executor, resource_dir):
    client_ip, client_port = addr
    print(f"Connection from {client_ip} {client_port}")
    try: 
        while True:
            # recieve data and encode it
            raw_data = conn.recv(8192).decode("utf-8")
            # Error Handling
            if not raw_data:
                break
            request_lines = raw_data.splitlines()
            if len(request_lines) == 0:
                response = make_response(400, "Bad Request", error_page("400", "Bad Request", "Request Empty"), extra_headers=["Connection: close"])
                conn.sendall(response)
                print(" --> 400 Bad Request")
                return
            # extracting header info from the request and storing it in dictionary
            request_headers = {}
            for line in request_lines:
                if line.strip() == "":
                    break
                if ":" in line:
                    k, v = line.split(":", 1)
                    request_headers[k.lower().strip()] = v.strip()

            # checking connection status. If connection close, break the loop
            connection_status = request_headers.get("connection", "close").lower()
            if connection_status == "close":
                print("LOG: Client requested to terminate the connection. Terminating...")
                keep_alive = False
            else:
                print("LOG: Maintaining Persistent Connection")
                keep_alive = True
            if not keep_alive:
                break
            
            # extract method, path, version from the first line of request and check each varable
            request_line = request_lines[0].strip()
            parts = request_line.split(" ")
            if len(parts) != 3: 
                response = make_response(400, "Bad Request", error_page("400", "Bad Request", "Malformed Request"), extra_headers=["Connection: close"])
                conn.sendall(response)
                print(" --> 400 Bad Request")
                return
            method, path, version = parts
            # version check
            if version not in ("HTTP/1.1", "HTTP/1.0"):
                response = make_response(505, "Version not Supported", error_page("505", "Version not supported", "Wrong HTTP version"), "close")
                conn.sendall(response)
                print(" --> 505 Version not supported")
            # process the response according to method
            if method.upper() == "GET":
                # resolve the path 
                ok, error_or_path = resolve_path(resource_dir, path)
                path = error_or_path
                # check if resolved path correctly or not
                if not ok:
                    response = make_response(403, "Forbidden", error_page("403", "Forbidden", "Forbidden Path"), "close")
                    conn.sendall(response)
                    print(" --> 403 Forbidden")
                    return
                # check if file or path exists to the given path
                if not os.path.exists(path) or not os.path.isfile(path):
                    response = make_response(404, "Bad Request", error_page("404", "Bad Request", "Reequested resource not found"), "close")
                    conn.sendall(response)
                    print(" --> 404 Not Found")
                    return
                try:
                    if path.endswith(".html"):
                        with open(path, "r", encoding="utf-8") as f:
                            data = f.read()
                        
                        extra_headers = [
                            "Connection: keep-alive",
                            "Keep-Alive: timeout=30, max=100"
                        ]
                        response = make_response(200, "OK", data, extra_headers=extra_headers)   
                        conn.sendall(response)
                        print(" --> 200 OK")
                    elif path.endswith((".png", ".jpeg", ".jpg", ".txt")):
                        with open(path, "rb") as f:
                            data = f.read()
                        extra_headers = [
                            "Connection: keep-alive",
                            "Keep-Alive: timeout=30, max=100"
                        ]
                        response = make_response(200, "OK", data, content_type="application/octet-stream", extra_headers=extra_headers)
                        conn.sendall(response)
                        print(" --> 200 OK")
                    else:
                        response = make_response(415, "Unsupported Media Type", error_page("415", "Unsupported Media Type", "File type not supported"))
                except Exception as e:
                    print(f" --> 500 Internal Server Error 2: {e}")
            elif method.upper() == "POST":
                if path != "/upload":
                    response = make_response(404, "Not Found", error_page("404", "Not Found", "The requested resource was not found."), extra_headers=["Connection: close"])
                    conn.sendall(response)
                    print(" --> 404 Not Found")
                    break 

                # validate if the content0type is in json (application/json)
                if request_headers.get("content-type", "").lower() != "application/json":
                    response = make_response(415, "Unsupported Media Type", error_page("415", "Unsupported Media Type", "Content-Type must be application/json."), extra_headers=["Connection: close"])
                    conn.sendall(response)
                    print(" --> 415 Unsupported Media Type")
                    return

                # 3. Validate the Content-Length header
                content_length_str = request_headers.get("content-length")
                if not content_length_str:
                    response = make_response(411, "Length Required", error_page("411", "Length Required", "Content-Length header is required for POST requests."), extra_headers=["Connection: close"])
                    conn.sendall(response)
                    print(" --> 411 Length Required")
                    break
                
                # try to get content-length, use try catch for debugging
                try:
                    content_length = int(content_length_str)
                except ValueError:
                    response = make_response(400, "Bad Request", error_page("400", "Bad Request", "Invalid Content-Length value."), extra_headers=["Connection: close"])
                    conn.sendall(response)
                    print(" --> 400 Bad Request")
                    return

                # split body from header by using \r\n\r\n --> this is http request response format to separate header from body
                body_string = raw_data.split("\r\n\r\n")[1]
                
                body_bytes = body_string.encode("utf-8")

                # Keep receiving data until the body is complete
                while len(body_bytes) < content_length:
                    chunk = conn.recv(4096)
                    if not chunk:
                        # Connection closed before we got the full body
                        print(" --> Connection closed prematurely by client")
                        break
                    body_bytes += chunk
                
                # Check if the connection was broken prematurely
                if len(body_bytes) < content_length:
                    break
                # decode the body_bytes
                # use json.loads method to convert the input data in JSON format to Oject in python. This is called parsing
                try:
                    body_str = body_bytes.decode("utf-8")
                    parsed_json = json.loads(body_str)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    response = make_response(400, "Bad Request", error_page("400", "Bad Request", "Invalid JSON or UTF-8 decoding error."), extra_headers=["Connection: close"])
                    conn.sendall(response)
                    print(" --> 400 Bad Request (Invalid JSON)")
                    return

                # get the request upload path after verifying it
                ok, path_or_error = resolve_upload_path(resource_dir)
                if not ok:
                    response = make_response(403, "Forbidden", error_page("403", "Forbidden", "Cannot create file in the specified location."), extra_headers=["Connection: close"])
                    conn.sendall(response)
                    print(" --> 403 Forbidden")
                    return

                file_path = path_or_error
                # open file_path in write mode and use json.dump to "dump" the data in the file.
                # "dump" means to convert python data structure to JSON format and save to file
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(parsed_json, f, indent=4)

                # successfully created file message
                response_body_dict = {
                    "status": "success",
                    "message": "File created successfully",
                    "filepath": "/uploads/" + os.path.basename(file_path)
                }
                response_body_json = json.dumps(response_body_dict)

                response = make_response(201, "Created", response_body_json, content_type="application/json; charset=utf-8")
                conn.sendall(response)
                print(f" --> 201 Created: {os.path.basename(file_path)}")

            else:
                response = make_response(405, "Method Not Allowed", error_page(""), extra_headers=["Connection: close"])
    except (socket.timeout, ConnectionResetError):
        print(f"Connection from {addr} timed out or was reset.")
            
    except:
        response = make_response(500, "Internal Server Error", "Internal Server Error", extra_headers=["Connection: close"])
        conn.sendall(response)
        print(" --> 500 Internal Server Error 1")
        return
    finally:
        conn.close()

        lock.acquire()
        global no_of_clients
        no_of_clients-=1
        if client_que:
            client = client_que.popleft()
            next_conn, next_addr = client
            executor.submit(handle_client_connection, next_conn, next_addr, executor, resource_dir)
        lock.release()

def resolve_upload_path(resource_dir):
    # make filepath in the prescribed directory
    uploads_dir = os.path.join(resource_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    # generate unique filename
    file_name = f"uploads_{int(time.time())}.json"
    candidate_path = os.path.realpath(os.path.join(uploads_dir, file_name))

    # security check
    actual_path = os.path.realpath(uploads_dir)

    if not candidate_path.startswith(actual_path + os.path.sep):
        return False, "403 Forbidden"
    return True, candidate_path
    
def resolve_path(resource_dir, path):
    # make the default path to index.html
    if path == "" or path == "/":
        path = "/index.html"

    path = path.lstrip("/") # removing the leading slash
    candidate_path = os.path.join(resource_dir, path) # joining the resource dir path with the requested path

    candidate_real = os.path.realpath(candidate_path)
    resource_real = os.path.realpath(resource_dir)
    resource_prefix = resource_real + os.path.sep
    if not candidate_real.startswith(resource_prefix): # Ensuring if the requested path is correct or not
        return False, "403 Forbidden"
    return True, candidate_real

def make_response(status_code, reason, body_html, content_type = "text/html; charset=utf-8", extra_headers=None):
    if body_html == "":
        body = b""
    if isinstance(body_html, str):
        body = body_html.encode("utf-8")
    else:
        body = body_html
    headers = [
        f"HTTP/1.1 {status_code} {reason}",
        f"Content-Type: {content_type}",
        f"Content-Length: {len(body)}",
        f"Date: {formatdate(timeval=None, usegmt=True)}",
        "Server: Multi-threaded HTTP Server",
    ]
    if extra_headers:
        headers.extend(extra_headers)
    header_blob = "\r\n".join(headers) + "\r\n\r\n"
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
            INTERFACE = str(sys.argv[2])
        if len(sys.argv) >= 4:
            threadpool_size = int(sys.argv[3])
    
    base_dir = os.path.dirname(os.path.realpath(__file__))
    resource_dir = os.path.join(base_dir, resources)

    start_server(PORT, INTERFACE, resource_dir, threadpool_size)
