import requests
import json
import os
from bs4 import BeautifulSoup
import hashlib

# Company career pages to monitor
COMPANIES = {
    # Major Humanoid/Robotics
    "Boston Dynamics": "https://careers.bostondynamics.com/",
    "Tesla": "https://www.tesla.com/careers/search/?keyword=internship",
    "Figure AI": "https://www.figure.ai/careers",
    "Agility Robotics": "https://boards.greenhouse.io/agilityrobotics",
    "1X Technologies": "https://www.1x.tech/careers",
    
    # Research Labs
    "Toyota Research": "https://www.tri.global/careers",
    "Honda Research": "https://hri-us.com/careers",
    "NVIDIA Robotics": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
    
    # AI Companies doing robotics
    "DeepMind": "https://deepmind.google/careers/",
    
    # Startups
    "Apptronik": "https://apptronik.com/careers",
    "Robust AI": "https://www.robust.ai/careers",
}
# Keywords to look for
KEYWORDS = ["reinforcement learning", "rl", "humanoid", "internship", "intern", "Imitation Learning"]

def get_page_content(url):
    """Fetch page content safely"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        return response.text if response.status_code == 200 else None
    except:
        return None

def extract_job_listings(html, company_name):
    """Extract job listings from HTML - customize per company"""
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    jobs = []
    
    # Generic approach - look for common job listing patterns
    job_elements = soup.find_all(['a', 'div'], string=lambda text: 
        text and any(keyword.lower() in text.lower() for keyword in KEYWORDS))
    
    for element in job_elements[:5]:  # Limit to avoid spam
        text = element.get_text(strip=True)
        if len(text) > 10 and len(text) < 200:  # Reasonable job title length
            jobs.append(text)
    
    return jobs

def load_previous_jobs():
    """Load previously found jobs"""
    try:
        with open('previous_jobs.json', 'r') as f:
            return json.load(f)
    except:
        return {}

def save_current_jobs(jobs):
    """Save current jobs for next comparison"""
    with open('previous_jobs.json', 'w') as f:
        json.dump(jobs, f, indent=2)

def send_notification(new_jobs):
    """Send Slack notification for new jobs"""
    if not new_jobs:
        return
    
    # Use GitHub Secrets for Slack webhook
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    
    if not webhook_url:
        print("Slack webhook URL not set")
        return
    
    # Create message
    total_jobs = sum(len(jobs) for jobs in new_jobs.values())
    message = f"🚨 *{total_jobs} New RL/Robotics Jobs Found!*\n\n"
    
    for company, jobs in new_jobs.items():
        message += f"🏢 *{company}*:\n"
        for job in jobs:
            message += f"  • {job}\n"
        message += "\n"
    
    # Slack webhook payload
    payload = {
        "text": message,
        "username": "Job Monitor Bot",
        "icon_emoji": ":robot_face:"
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            print(f"✅ Slack notification sent for {len(new_jobs)} companies")
        else:
            print(f"❌ Failed to send Slack message: {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to send Slack notification: {e}")

def main():
    print("🔍 Starting job monitoring...")
    
    previous_jobs = load_previous_jobs()
    current_jobs = {}
    new_jobs = {}
    
    for company, url in COMPANIES.items():
        print(f"Checking {company}...")
        
        html = get_page_content(url)
        jobs = extract_job_listings(html, company)
        
        if jobs:
            current_jobs[company] = jobs
            
            # Check for new jobs
            prev_jobs = set(previous_jobs.get(company, []))
            curr_jobs = set(jobs)
            new_job_titles = curr_jobs - prev_jobs
            
            if new_job_titles:
                new_jobs[company] = list(new_job_titles)
                print(f"🆕 Found {len(new_job_titles)} new jobs at {company}")
            else:
                print(f"✅ No new jobs at {company}")
        else:
            print(f"⚠️  No relevant jobs found at {company}")
    
    # Save current state
    save_current_jobs(current_jobs)
    
    # Send notifications
    if new_jobs:
        send_notification(new_jobs)
        print(f"🎉 Total new opportunities: {sum(len(jobs) for jobs in new_jobs.values())}")
    else:
        print("😴 No new jobs found this time")

if __name__ == "__main__":
    main()