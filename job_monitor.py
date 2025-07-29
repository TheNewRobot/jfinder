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

# Keywords - ONLY internships, with technical preferences
INTERNSHIP_KEYWORDS = ["internship", "intern", "co-op", "coop"]  # Must have one of these
TECHNICAL_KEYWORDS = ["reinforcement learning", "rl", "humanoid", "imitation learning", "robotics", "ai controls", "machine learning", "ml", "controls", "embodied ai"]  # Technical preferences

def get_page_content(url):
    """Fetch page content safely"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        return response.text if response.status_code == 200 else None
    except:
        return None

def extract_job_listings(html, company_name):
    """Extract ONLY actual internship job postings - company-specific parsing"""
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    jobs = []
    
    # Company-specific parsing strategies
    if "greenhouse.io" in company_name.lower() or "greenhouse" in html.lower():
        # Greenhouse job board parsing
        job_elements = soup.find_all(['div', 'a'], attrs={
            'class': lambda x: x and any(cls in str(x).lower() for cls in ['opening', 'job', 'position'])
        })
        # Also try direct job links
        job_links = soup.find_all('a', href=lambda x: x and '/jobs/' in str(x))
        job_elements.extend(job_links)
        
    elif "workday" in html.lower() or "myworkdayjobs" in company_name.lower():
        # Workday job board parsing
        job_elements = soup.find_all(['div', 'a'], attrs={
            'data-automation-id': True
        })
        job_elements.extend(soup.find_all('a', href=lambda x: x and 'job' in str(x).lower()))
        
    elif "lever.co" in html.lower():
        # Lever job board parsing
        job_elements = soup.find_all(['div', 'a'], attrs={
            'class': lambda x: x and 'posting' in str(x).lower()
        })
        
    elif "breezy" in html.lower():
        # BreezyHR parsing
        job_elements = soup.find_all(['div', 'li'], attrs={
            'class': lambda x: x and any(cls in str(x).lower() for cls in ['position', 'job'])
        })
        
    else:
        # Generic parsing for company career pages
        # Look for common job listing patterns
        job_elements = []
        
        # Method 1: Look for elements with job-related classes/IDs
        job_containers = soup.find_all(['div', 'li', 'article', 'section'], attrs={
            'class': lambda x: x and any(keyword in str(x).lower() for keyword in [
                'job', 'position', 'opening', 'role', 'career', 'listing', 'opportunity'
            ])
        })
        job_elements.extend(job_containers)
        
        # Method 2: Look for links that contain job-related URLs
        job_links = soup.find_all('a', href=lambda x: x and any(keyword in str(x).lower() for keyword in [
            'job', 'position', 'career', 'opening', 'role'
        ]))
        job_elements.extend(job_links)
        
        # Method 3: Look for structured data (JSON-LD job postings)
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                    title = data.get('title', '')
                    if any(keyword.lower() in title.lower() for keyword in INTERNSHIP_KEYWORDS):
                        jobs.append(f"🔍 {title}")
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                            title = item.get('title', '')
                            if any(keyword.lower() in title.lower() for keyword in INTERNSHIP_KEYWORDS):
                                jobs.append(f"🔍 {title}")
            except:
                continue
    
    # Process found elements
    for element in job_elements:
        # Get text content
        if element.name == 'a' and element.get('href'):
            # For links, prefer the link text
            text = element.get_text(strip=True)
            if not text:  # If link has no text, try title attribute
                text = element.get('title', '')
        else:
            text = element.get_text(strip=True)
        
        # Filter for internships only
        if not text or len(text) < 10 or len(text) > 300:
            continue
            
        text_lower = text.lower()
        
        # Must contain internship keywords
        if not any(keyword.lower() in text_lower for keyword in INTERNSHIP_KEYWORDS):
            continue
            
        # Skip generic/navigation text
        skip_phrases = [
            'view all', 'see all', 'browse', 'search jobs', 'job search',
            'careers home', 'back to', 'apply now', 'learn more',
            'follow us', 'join our', 'about us', 'contact us',
            'sign up', 'subscribe', 'newsletter', 'follow along'
        ]
        
        if any(skip in text_lower for skip in skip_phrases):
            continue
            
        # Clean up the text
        text = ' '.join(text.split())  # Remove extra whitespace
        
        # Check for technical relevance
        if any(tech_keyword.lower() in text_lower for tech_keyword in TECHNICAL_KEYWORDS):
            jobs.append(f"⭐ {text}")  # High relevance
        else:
            jobs.append(text)  # Regular internship
    
    # Remove duplicates while preserving order
    seen = set()
    unique_jobs = []
    for job in jobs:
        if job not in seen:
            seen.add(job)
            unique_jobs.append(job)
            if len(unique_jobs) >= 5:  # Limit to avoid spam
                break
    
    return unique_jobs

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
    message = f"🚨 *{total_jobs} New Internship Opportunities!*\n\n"
    
    for company, jobs in new_jobs.items():
        message += f"🏢 *{company}*:\n"
        for job in jobs:
            message += f"  • {job}\n"
        message += "\n"
    
    # Slack webhook payload
    payload = {
        "text": message,
        "username": "Internship Monitor Bot",
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
    print("🔍 Starting internship monitoring...")
    
    previous_jobs = load_previous_jobs()
    current_jobs = {}
    new_jobs = {}
    
    for company, url in COMPANIES.items():
        print(f"\n🔍 Checking {company}...")
        print(f"   URL: {url}")
        
        html = get_page_content(url)
        if not html:
            print(f"   ❌ Could not fetch page")
            continue
            
        jobs = extract_job_listings(html, company)
        
        if jobs:
            print(f"   ✅ Found {len(jobs)} relevant posting(s):")
            for job in jobs:
                print(f"      • {job}")
                
            current_jobs[company] = jobs
            
            # Check for new jobs
            prev_jobs = set(previous_jobs.get(company, []))
            curr_jobs = set(jobs)
            new_job_titles = curr_jobs - prev_jobs
            
            if new_job_titles:
                new_jobs[company] = list(new_job_titles)
                print(f"   🆕 {len(new_job_titles)} are NEW!")
            else:
                print(f"   ℹ️  All previously seen")
        else:
            print(f"   ⚠️  No relevant internships found")
    
    # Save current state
    save_current_jobs(current_jobs)
    
    # Send notifications
    if new_jobs:
        print(f"\n🎉 Sending notification for {sum(len(jobs) for jobs in new_jobs.values())} new opportunities!")
        send_notification(new_jobs)
    else:
        print("\n😴 No new internships found this time")
    
    print("\n✅ Monitoring complete!")

if __name__ == "__main__":
    main()