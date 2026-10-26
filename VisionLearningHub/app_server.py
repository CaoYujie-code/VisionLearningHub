"""Desktop launcher and worker share this entry point, without importing web code in workers."""
import sys

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        from learning.engine import worker
        worker(sys.argv[2])
    else:
        import argparse
        import uvicorn
        parser = argparse.ArgumentParser()
        parser.add_argument('--port', type=int, default=8766)
        parser.add_argument('--managed', action='store_true')
        args = parser.parse_args()
        from backend.server import app
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=args.port, log_level='info'))
        app.state.uvicorn_server = server
        if args.managed:
            import threading
            import os
            parent_pipe = sys.stdin.fileno()
            def parent_closed():
                while os.read(parent_pipe, 4096):
                    pass
                from backend.server import LOCK, JOBS
                with LOCK:
                    for job in JOBS.values():
                        if job.get('process') and job['process'].poll() is None:
                            job['process'].kill()
                    server.should_exit = True
            threading.Thread(target=parent_closed, daemon=True).start()
        server.run()
