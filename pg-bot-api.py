from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/")
@app.get("/")
async def root():
    return {"status": "OK", "version":"0.0.3"}

@app.post("/echo")
@app.get("/echo")
async def echo(request: Request):
    return await request.body()
    """
    return {
            "method": str(request.method),
            "url": str(request.url),
            "headers": str(request.headers),
            "body": str(request.body()),
            "client-addr": str(request.client)
        }
    """    