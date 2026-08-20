const http = require("http");
const fs = require("fs");
const path = require("path");

const port = process.env.PORT || 8000;
const page = path.join(__dirname, "index.html");

http
  .createServer((request, response) => {
    if (request.url !== "/" && request.url !== "/index.html") {
      response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      response.end("Not found");
      return;
    }

    response.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    fs.createReadStream(page).pipe(response);
  })
  .listen(port, () => {
    console.log(`Sora Sushi is running at http://localhost:${port}`);
  });
