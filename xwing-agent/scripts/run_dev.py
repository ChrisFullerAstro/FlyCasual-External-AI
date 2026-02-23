"""Run development server."""
import uvicorn

PORT = 33293

if __name__ == "__main__":
    print(f"\n{'='*50}")
    print(f"  X-Wing AI Agent starting on port {PORT}")
    print(f"  URL: http://localhost:{PORT}")
    print(f"  API docs: http://localhost:{PORT}/docs")
    print(f"{'='*50}\n")

    uvicorn.run(
        "xwing_agent.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
    )
