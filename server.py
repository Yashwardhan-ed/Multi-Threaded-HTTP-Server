import socket
import concurrent.futures
import os
import time
import threading


interface = "127.0.0.1"
port = 8080
client_que = []
clients = 0
lock = threading.Lock()

def start_server(port, interface, maxPoolSize=10):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((interface, port))
    sock.listen()
    with concurrent.futures.ThreadPoolExecutor(max_workers=maxPoolSize) as executor:
        conn, addr = sock.accept()
        no_of_clients+=1
        executor.submit(handle_client_connection, conn, addr, executor)
    if clients >= maxPoolSize:
        print("Thread pool saturated, queing connection")
        client_que.append((conn, addr))



def handle_client_connection(conn, addr, executor):
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
            exec
        lock.release()

            


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
    start_server()