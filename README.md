# 🧭 Multi-Threaded HTTP Server

This project implements a simple **multi-threaded HTTP server** in Python.  
The server supports **GET** and **POST** methods, serves static files (HTML, text, images), and allows uploading JSON data to the server via POST requests.

---

##  Features

- ✅ **GET method** to serve:
  - HTML files
  - Text files
  - PNG and JPEG images (including large files >1 MB)
- ✅ **POST method** to upload JSON files into a secure `uploads/` directory
- ✅ **Multi-threaded server** using `ThreadPoolExecutor`  
- ✅ **Connection queueing** when thread pool is saturated
- ✅ Path resolution with security checks (prevents directory traversal)
- ✅ Proper HTTP response codes and headers
- ✅ Configurable server interface, port, and thread pool size via CLI

---

##  **Project Structure**

* `project/`
    * `server.py`
    * `README.md`
    * `resources/`
        * `index.html`
        * `about.html`
        * `contact.html`
        * `Meme.png`
        * `stateuofliberty.png`
        * `bird.jpg`
        * `Neutron_Star.jpg`
        * `banana.txt`
        * `list_voices.txt`
        * `sample_post.json`
        * `uploads/`

---

## **How to Run**

### Install Python  
Make sure you have **Python 3.8+** installed.  
Check with:
```bash
python3 --version
Start the Server
bash
python3 server.py [PORT] [INTERFACE] [THREADPOOL_SIZE]
Example:

bash
python3 server.py 8080 127.0.0.1 10
PORT → (optional) Defaults to 8080

INTERFACE → (optional) Defaults to 127.0.0.1

THREADPOOL_SIZE → (optional) Defaults to 10

 Supported Endpoints
GET
Serve static files from the resources/ folder.

Examples:

bash
curl http://127.0.0.1:8080/index.html
curl http://127.0.0.1:8080/images/logo.png --output logo.png
curl http://127.0.0.1:8080/texts/sample1.txt
POST
Upload JSON files to the server.
Target endpoint:

POST http://127.0.0.1:8080/upload
Headers:

Content-Type: application/json
Example using curl:

bash
curl -X POST http://127.0.0.1:8080/upload \
     -H "Content-Type: application/json" \
     -d @resources/sample_post.json

Response:

json
{
  "status": "success",
  "message": "File created successfully",
  "filepath": "/uploads/upload_1727522345.json"
}

Uploaded files are stored under:

bash
resources/uploads/
 Test Files
The resources/ directory contains a set of test files used to validate the server:

 HTML: 3 files (index.html, about.html, contact.html)

 Text: 2 files

 PNG: 2 files (1 is >1 MB to test large transfers)

 JPEG: 2 files

 JSON: Sample JSON for POST testing

You can add your own files to resources/ to test more scenarios.

 Testing the Server
GET Requests
bash
curl http://127.0.0.1:8080/about.html
curl http://127.0.0.1:8080/images/large_image.png --output test.png
POST Requests (JSON Upload)
bash
curl -X POST http://127.0.0.1:8080/upload \
     -H "Content-Type: application/json" \
     -d '{"user":"Yash","message":"Hello Server"}'
Key Implementation Details:

1. ThreadPoolExecutor manages active client connections.

2. A deque queue temporarily holds excess clients when the pool is full.

3. Locks ensure thread-safe updates of shared variables.

4. os.path.realpath is used to validate all resolved paths to prevent directory traversal.

5. Responses include proper HTTP headers (Content-Length, Date, Server, Connection, etc.).

6. Upload paths are checked before writing files.
---
