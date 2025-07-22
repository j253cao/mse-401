#!/usr/bin/env python3
"""
Script to export all course API data to a single JSON file.
This allows for batch processing with Cursor's AI to parse requirements.
"""

import os
import json
import sys
import time
import traceback
import smtplib
import platform
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.data_loader import load_full_courses
from utils.course_dependency_builder import get_course_data

# Configuration for alerts
ALERT_CONFIG = {
    'email_enabled': False,  # Set to True and configure below to enable email alerts
    'email_sender': 'your-email@gmail.com',
    'email_password': 'your-app-password',  # Use app password for Gmail
    'email_recipient': 'your-email@gmail.com',
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'desktop_notifications': True,  # Enable desktop notifications
    'log_file': 'export_log.txt'
}

def send_email_alert(subject, message):
    """Send email alert if configured."""
    if not ALERT_CONFIG['email_enabled']:
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = ALERT_CONFIG['email_sender']
        msg['To'] = ALERT_CONFIG['email_recipient']
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain'))
        
        server = smtplib.SMTP(ALERT_CONFIG['smtp_server'], ALERT_CONFIG['smtp_port'])
        server.starttls()
        server.login(ALERT_CONFIG['email_sender'], ALERT_CONFIG['email_password'])
        text = msg.as_string()
        server.sendmail(ALERT_CONFIG['email_sender'], ALERT_CONFIG['email_recipient'], text)
        server.quit()
        
        print(f"📧 Email alert sent: {subject}")
    except Exception as e:
        print(f"❌ Failed to send email alert: {e}")

def send_desktop_notification(title, message):
    """Send desktop notification if supported."""
    if not ALERT_CONFIG['desktop_notifications']:
        return
    
    try:
        system = platform.system()
        
        if system == "Windows":
            # Windows notification
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=10, threaded=True)
        elif system == "Darwin":
            # macOS notification
            os.system(f"""
                osascript -e 'display notification "{message}" with title "{title}"'
            """)
        elif system == "Linux":
            # Linux notification
            os.system(f'notify-send "{title}" "{message}"')
        else:
            print(f"⚠️  Desktop notifications not supported on {system}")
            
    except ImportError:
        print("⚠️  win10toast not installed. Install with: pip install win10toast")
    except Exception as e:
        print(f"❌ Failed to send desktop notification: {e}")

def log_message(message, level="INFO"):
    """Log message to file."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {level}: {message}\n"
    
    try:
        with open(ALERT_CONFIG['log_file'], 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"❌ Failed to write to log file: {e}")

def send_alert(subject, message, level="INFO"):
    """Send alert through all configured channels."""
    log_message(message, level)
    
    if level in ["ERROR", "CRITICAL"]:
        send_email_alert(subject, message)
        send_desktop_notification(subject, message)
        print(f"🚨 ALERT: {subject}")
        print(f"📝 {message}")

def load_checkpoint():
    """Load progress from checkpoint file."""
    checkpoint_file = Path("export_checkpoint.json")
    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                print(f"📂 Found checkpoint: {checkpoint['processed_count']} courses already processed")
                log_message(f"Resumed from checkpoint: {checkpoint['processed_count']} courses")
                return checkpoint
        except Exception as e:
            error_msg = f"Could not load checkpoint: {e}"
            print(f"⚠️  {error_msg}")
            log_message(error_msg, "WARNING")
    return {'processed_count': 0, 'course_data_map': {}}

def save_checkpoint(processed_count, course_data_map):
    """Save progress to checkpoint file."""
    checkpoint_file = Path("export_checkpoint.json")
    checkpoint = {
        'processed_count': processed_count,
        'course_data_map': course_data_map,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    try:
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        print(f"💾 Checkpoint saved at {processed_count} courses")
        log_message(f"Checkpoint saved at {processed_count} courses")
    except Exception as e:
        error_msg = f"Failed to save checkpoint: {e}"
        print(f"❌ {error_msg}")
        send_alert("Export Checkpoint Error", error_msg, "ERROR")

def export_single_course_data(course):
    """Export all API data for a single course."""
    try:
        # Get complete course data from API
        course_data = get_course_data(course['pid'])
        
        # Add course metadata
        complete_data = {
            'courseCode': course['courseCode'],
            'title': course['title'],
            'department': course['department'],
            'pid': course['pid'],
            'api_data': course_data
        }
        
        print(f"✅ Exported complete data for {course['courseCode']}")
        return complete_data
        
    except Exception as e:
        error_msg = f"Error exporting {course['courseCode']}: {str(e)}"
        print(f"❌ {error_msg}")
        log_message(error_msg, "ERROR")
        return None

def export_all_course_data(limit=None, batch_size=10):
    """Export all API data for all courses to a single JSON file with checkpoint support."""
    start_time = time.time()
    print("🚀 Starting complete course data export...")
    log_message("Starting complete course data export")
    
    try:
        # Load checkpoint to resume from where we left off
        checkpoint = load_checkpoint()
        course_data_map = checkpoint['course_data_map']
        start_index = checkpoint['processed_count']
        
        # Load all courses
        print("📚 Loading course data...")
        full_courses = load_full_courses()
        
        if not full_courses:
            error_msg = "No courses found!"
            print(f"❌ {error_msg}")
            send_alert("Export Failed", error_msg, "ERROR")
            return None
        
        print(f"📖 Found {len(full_courses)} courses")
        log_message(f"Found {len(full_courses)} courses")
        
        # Limit courses if specified
        if limit:
            full_courses = full_courses[:limit]
            print(f"🔢 Limiting to first {limit} courses")
            log_message(f"Limited to first {limit} courses")
        
        # Skip already processed courses
        courses_to_process = full_courses[start_index:]
        print(f"🔄 Resuming from course {start_index + 1}, {len(courses_to_process)} courses remaining")
        
        # Export data for each course with rate limiting
        successful_exports = 0
        failed_exports = 0
        consecutive_failures = 0
        max_consecutive_failures = 5
        
        for i, course in enumerate(courses_to_process, start_index + 1):
            print(f"\n📋 Processing {i}/{len(full_courses)}: {course['courseCode']}")
            
            try:
                course_data = export_single_course_data(course)
                
                if course_data:
                    course_data_map[course['courseCode']] = course_data
                    successful_exports += 1
                    consecutive_failures = 0  # Reset consecutive failure counter
                else:
                    failed_exports += 1
                    consecutive_failures += 1
                
                # Check for too many consecutive failures
                if consecutive_failures >= max_consecutive_failures:
                    error_msg = f"Too many consecutive failures ({consecutive_failures}). Stopping export."
                    print(f"❌ {error_msg}")
                    send_alert("Export Stopped - Too Many Failures", error_msg, "ERROR")
                    break
                
                # Save checkpoint every batch_size courses
                if i % batch_size == 0:
                    save_checkpoint(i, course_data_map)
                
                # Rate limiting: 2 requests per second = 0.5 seconds between requests
                if i < len(full_courses):  # Don't sleep after the last request
                    print("⏳ Rate limiting: waiting 0.5 seconds...")
                    time.sleep(0.5)
                    
            except KeyboardInterrupt:
                print("\n⚠️  Export interrupted by user")
                log_message("Export interrupted by user", "WARNING")
                send_alert("Export Interrupted", "Export was interrupted by user", "WARNING")
                save_checkpoint(i, course_data_map)
                return None
                
            except Exception as e:
                error_msg = f"Unexpected error processing {course['courseCode']}: {str(e)}"
                print(f"❌ {error_msg}")
                log_message(error_msg, "ERROR")
                failed_exports += 1
                consecutive_failures += 1
        
        # Save final results to JSON file
        output_file = Path("course-api-data.json")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(course_data_map, f, indent=2, ensure_ascii=False)
        except Exception as e:
            error_msg = f"Failed to save output file: {e}"
            print(f"❌ {error_msg}")
            send_alert("Export Failed - Save Error", error_msg, "ERROR")
            return None
        
        # Clean up checkpoint file after successful completion
        checkpoint_file = Path("export_checkpoint.json")
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            print("🧹 Checkpoint file cleaned up")
        
        # Calculate duration
        duration = time.time() - start_time
        duration_str = f"{duration:.2f} seconds"
        
        # Create summary
        summary = {
            "total_courses": len(full_courses),
            "successful_exports": successful_exports,
            "failed_exports": failed_exports,
            "output_file": str(output_file.absolute()),
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "duration": duration_str,
            "rate_limit": "2 requests per second",
            "batch_size": batch_size
        }
        
        success_msg = f"Export completed successfully in {duration_str}"
        print(f"\n🎉 {success_msg}")
        print(f"✅ Successful exports: {successful_exports}")
        print(f"❌ Failed exports: {failed_exports}")
        print(f"📁 JSON file saved to: {output_file.absolute()}")
        print(f"📊 Total course codes in JSON: {len(course_data_map)}")
        print(f"⏱️  Rate limit applied: 2 requests per second")
        
        log_message(success_msg)
        send_alert("Export Completed Successfully", 
                  f"Successfully exported {successful_exports} courses in {duration_str}", 
                  "INFO")
        
        return output_file
        
    except Exception as e:
        error_msg = f"Critical error during export: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ {error_msg}")
        send_alert("Export Failed - Critical Error", error_msg, "CRITICAL")
        return None

def create_cursor_batch_prompt():
    """Create a prompt file for Cursor batch processing."""
    prompt = '''# Cursor Batch Processing Prompt

Parse the course-api-data.json file which contains a mapping of course codes to their complete API data including prerequisites, corequisites, and antirequisites.

## Expected JSON Format for Each Course:
```json
{
  "prerequisite": {
    "type": "all|one_of",
    "rules": [
      {
        "type": "course_requirement",
        "code": "CS135",
        "description": "CS135 - Introduction to Computer Science (0.50)"
      },
      {
        "type": "program_requirement", 
        "description": "H-Computer Science"
      }
    ]
  },
  "corequisite": {
    "type": "one_of",
    "rules": [...]
  },
  "antirequisite": {
    "type": "all",
    "rules": [...]
  }
}
```

## Instructions:
1. Parse the course-api-data.json file
2. For each course code and its API data, extract prerequisite, corequisite, and antirequisite information from the api_data field
3. Identify course codes, titles, and credits where available
4. Handle nested structures like "Complete all of the following" and "Complete 1 of the following"
5. Extract program requirements like "Enrolled in" statements
6. Group program requirements into "one_of" structures (since you can only be in one program)
7. Use only "one_of" or "all" as outer types
8. Return a JSON object mapping course codes to their parsed requirement structures

## Expected Output Format:
```json
{
  "MSE436": {
    "prerequisite": {
      "type": "one_of",
      "rules": [...]
    },
    "corequisite": null,
    "antirequisite": null
  }
}
```

## File Processing:
- Process the course-api-data.json file
- Extract requirement data from the api_data field for each course
- Return the complete mapping of course codes to parsed requirement structures
- Handle all course codes in the file
- Follow the interface structure with prerequisite, corequisite, and antirequisite fields
'''
    
    prompt_file = Path("CURSOR_BATCH_PROMPT.md")
    with open(prompt_file, 'w') as f:
        f.write(prompt)
    
    print(f"📝 Created Cursor batch prompt: {prompt_file}")

def main():
    """Main function."""
    print("=" * 60)
    print("📤 Complete Course API Data Export Tool")
    print("=" * 60)
    
    # Log start
    log_message("Export tool started")
    
    try:
        # Check for command line arguments
        limit = None  # Default to all courses
        batch_size = 10  # Default batch size for checkpoints
        
        if len(sys.argv) > 1:
            try:
                limit = int(sys.argv[1])
                print(f"🔢 Will limit export to first {limit} courses")
            except ValueError:
                print("⚠️  Invalid limit number, using all courses")
        else:
            print(f"🔢 Will export all courses")
        
        if len(sys.argv) > 2:
            try:
                batch_size = int(sys.argv[2])
                print(f"📦 Checkpoint batch size: {batch_size} courses")
            except ValueError:
                print("⚠️  Invalid batch size, using default of 10")
        else:
            print(f"📦 Using default checkpoint batch size of {batch_size} courses")
        
        print(f"⏱️  Rate limiting: 2 requests per second")
        
        # Export course data
        output_file = export_all_course_data(limit, batch_size)
        
        if output_file:
            # Create Cursor batch prompt
            create_cursor_batch_prompt()
            
            print("\n" + "=" * 60)
            print("🎯 Next Steps for Cursor Batch Processing:")
            print("=" * 60)
            print("1. Open the 'course-api-data.json' file in Cursor")
            print("2. Right-click and choose 'Ask Cursor' or 'Chat'")
            print("3. Use the prompt from CURSOR_BATCH_PROMPT.md")
            print("4. Cursor will process the entire file and return parsed JSON")
            print("5. Copy the result and save it as your parsed requirements")
            print("=" * 60)
            
            log_message("Export tool completed successfully")
        else:
            log_message("Export tool failed", "ERROR")
            
    except KeyboardInterrupt:
        print("\n⚠️  Export interrupted by user")
        log_message("Export interrupted by user", "WARNING")
        send_alert("Export Interrupted", "Export was interrupted by user", "WARNING")
        
    except Exception as e:
        error_msg = f"Unexpected error in main: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ {error_msg}")
        send_alert("Export Failed - Unexpected Error", error_msg, "CRITICAL")

if __name__ == "__main__":
    main() 