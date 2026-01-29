import asyncio
import aiohttp
import time

async def fetch(session, url):
    try:
        async with session.get(url) as response:
            return response.status
    except Exception as e:
        return 0

async def main():
    url = "http://localhost:8000/"
    total_requests = 100
    concurrent_requests = 20
    
    print(f"Starting load test on {url}")
    print(f"Total requests: {total_requests}, Concurrency: {concurrent_requests}")

    async with aiohttp.ClientSession() as session:
        tasks = []
        start_time = time.time()
        
        for i in range(total_requests):
            tasks.append(fetch(session, url))
            if len(tasks) >= concurrent_requests:
                await asyncio.gather(*tasks)
                tasks = []
                
        if tasks:
            await asyncio.gather(*tasks)
            
        duration = time.time() - start_time
        print(f"Finished in {duration:.2f} seconds")
        print(f"RPS: {total_requests / duration:.2f}")

if __name__ == "__main__":
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
