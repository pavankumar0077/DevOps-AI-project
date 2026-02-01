import os
import json
import time
import logging
from github import Github
from openai import OpenAI
import chromadb
from slack_sdk.webhook import WebhookClient

logger = logging.getLogger(__name__)

class AIHealingAgent:
    def __init__(self, github_token, openai_key, slack_webhook):
        self.gh = Github(github_token)
        self.openai = OpenAI(api_key=openai_key)
        self.slack = WebhookClient(slack_webhook) if slack_webhook else None
        
        # Initialize ChromaDB for vector storage
        # Using local persistence for simplicity in this demo
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.chroma_client.get_or_create_collection(
            name="pipeline_failures",
            metadata={"description": "Historical pipeline failure data"}
        )
        
        self.healing_stats = {"total_heals": 0, "successful_heals": 0}

    def heal_pipeline(self, request_data):
        """Main healing orchestration"""
        try:
            logger.info(f"🔧 Starting healing for run {request_data['run_id']}")
            
            # 1. Fetch failure details
            logs = self.fetch_pipeline_logs(request_data)
            logger.info("Logs fetched successfully.")
            
            # 2. Query similar past failures
            similar_failures = self.query_similar_failures(logs)
            
            # 3. Generate fix using LLM
            fix_recommendation = self.generate_fix(logs, similar_failures)
            logger.info(f"Fix recommendation generated: {fix_recommendation.get('root_cause')}")
            
            # 4. Store this failure for future learning
            self.store_failure(logs, fix_recommendation)
            
            # 5. Apply fix
            fix_applied = self.apply_fix(request_data, fix_recommendation)
            
            # 6. Notify team
            self.send_notification(request_data, fix_recommendation, fix_applied)
            
            self.healing_stats["total_heals"] += 1
            if fix_applied:
                self.healing_stats["successful_heals"] += 1
                
        except Exception as e:
            logger.error(f"❌ Healing failed: {str(e)}", exc_info=True)
            self.send_error_notification(request_data, str(e))

    def fetch_pipeline_logs(self, request_data):
        """Fetch logs from failed GitHub Actions run"""
        # Note: If running locally without real GitHub token, this will fail. 
        # For demo purposes, we can mock this if token is 'mock'.
        if self.gh.get_user().login == "mock-user": # Hypothetical check
             return {"mock": "logs"}

        repo = self.gh.get_repo(request_data['repo'])
        run = repo.get_workflow_run(int(request_data['run_id']))
        
        logs_data = {
            "conclusion": run.conclusion,
            "jobs": []
        }
        
        for job in run.jobs():
            if job.conclusion == "failure":
                # Getting raw logs can be tricky with PyGithub directly in some versions, 
                # often need to download zip. For simplicity we use steps analysis here
                # or simplified log retrieval.
                step_failures = []
                for step in job.steps:
                    if step.conclusion == "failure":
                        step_failures.append({
                            "name": step.name,
                            "conclusion": step.conclusion,
                            # getting actual log content requires run.timing() or separate API call usually
                            "logs": "Log content unavailable via simple API. Using step name as context." 
                        })
                logs_data["jobs"].append({
                    "name": job.name,
                    "steps": step_failures
                })
        
        return logs_data

    def query_similar_failures(self, logs):
        """Query ChromaDB for similar historical failures"""
        log_text = json.dumps(logs)
        
        # ChromaDB requires non-empty query
        results = self.collection.query(
            query_texts=[log_text],
            n_results=3
        )
        
        return results

    def generate_fix(self, logs, similar_failures):
        """Use LLM to generate fix recommendation"""
        
        context = f"""
You are an expert DevOps engineer analyzing a CI/CD pipeline failure.

Current Failure:
{json.dumps(logs, indent=2)}

Similar Past Failures:
{json.dumps(similar_failures, indent=2) if similar_failures and similar_failures['documents'] else "No similar failures found"}

Analyze the failure and provide:
1. Root cause
2. Recommended fix
3. Confidence level (high/medium/low)
4. Whether fix can be auto-applied (yes/no)
5. If yes, provide exact changes needed

Response format (JSON ONLY):
{{
  "root_cause": "...",
  "recommended_fix": "...",
  "confidence": "high",
  "auto_applicable": true,
  "changes": {{
    "file": "path/to/file",
    "type": "config|code|dependency",
    "patch": "new_content"
  }}
}}
"""
        try:
            response = self.openai.chat.completions.create(
                model="gpt-4-turbo-preview", # Use a smart model
                messages=[
                    {"role": "system", "content": "You are an expert DevOps AI agent. Output valid JSON only."},
                    {"role": "user", "content": context}
                ],
                temperature=0.3,
                response_format={ "type": "json_object" }
            )
            
            fix_json = response.choices[0].message.content
            return json.loads(fix_json)
        except Exception as e:
            logger.error(f"LLM Generation failed: {e}")
            return {
                "root_cause": "LLM Analysis Failed", 
                "recommended_fix": "Check logs manually", 
                "confidence": "low", 
                "auto_applicable": False
            }

    def store_failure(self, logs, fix):
        """Store failure in vector DB for future learning"""
        try:
            failure_text = json.dumps(logs)
            self.collection.add(
                documents=[failure_text],
                metadatas=[{
                    "fix": json.dumps(fix),
                    "timestamp": str(time.time())
                }],
                ids=[f"failure_{int(time.time())}"]
            )
        except Exception as e:
            logger.warn(f"Failed to store failure in Chroma: {e}")

    def apply_fix(self, request_data, fix):
        """Apply the fix by creating a PR or retrying"""
        
        if not fix.get("auto_applicable"):
            return False
        
        try:
            repo = self.gh.get_repo(request_data['repo'])
            base_branch_name = request_data['branch']
            base_branch = repo.get_branch(base_branch_name)
            new_branch_name = f"auto-fix-{request_data['run_id']}"
            
            # Check if branch exists
            try:
                repo.get_branch(new_branch_name)
                # If exists, maybe append timestamp
                new_branch_name = f"{new_branch_name}-{int(time.time())}"
            except:
                pass

            repo.create_git_ref(
                ref=f"refs/heads/{new_branch_name}",
                sha=base_branch.commit.sha
            )
            
            # Apply changes
            changes = fix.get("changes", {})
            if changes:
                file_path = changes.get("file")
                # Get current file content to get SHA
                try:
                    file_content = repo.get_contents(file_path, ref=new_branch_name)
                    sha = file_content.sha
                except:
                    sha = None # New file?
                
                # Apply patch (simplified - in production use diff tools)
                # In this simplified version, 'patch' is treated as 'full new content'
                new_content = changes.get("patch")
                
                if sha:
                    repo.update_file(
                        path=file_path,
                        message=f"🤖 Auto-fix: {fix.get('root_cause', 'Fix failure')}",
                        content=new_content,
                        sha=sha,
                        branch=new_branch_name
                    )
                else:
                    repo.create_file(
                        path=file_path,
                        message=f"🤖 Auto-fix: {fix.get('root_cause', 'Fix failure')}",
                        content=new_content,
                        branch=new_branch_name
                    )
            
            # Create PR
            pr = repo.create_pull(
                title=f"🤖 Auto-fix: Pipeline failure in run #{request_data['run_id']}",
                body=f"""
## AI-Generated Fix

**Root Cause:** {fix.get('root_cause')}

**Recommended Fix:** {fix.get('recommended_fix')}

**Confidence:** {fix.get('confidence')}

---
*This PR was automatically generated by the AI Healing Agent.*
*Please review before merging.*
                """,
                head=new_branch_name,
                base=base_branch_name
            )
            
            logger.info(f"PR Created: {pr.html_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply fix: {str(e)}")
            return False

    def send_notification(self, request_data, fix, fix_applied):
        """Send Slack notification"""
        if not self.slack:
            logger.info("Slack webhook not configured, skipping notification.")
            return

        status_emoji = "✅" if fix_applied else "⚠️"
        status_text = "Auto-fix applied" if fix_applied else "Manual review needed"
        
        message = {
            "text": f"{status_emoji} Pipeline Healing Report",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{status_emoji} AI Healing Agent Report"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Repository:*\n{request_data['repo']}"},
                        {"type": "mrkdwn", "text": f"*Run ID:*\n#{request_data['run_id']}"},
                        {"type": "mrkdwn", "text": f"*Status:*\n{status_text}"},
                        {"type": "mrkdwn", "text": f"*Confidence:*\n{fix.get('confidence', 'unknown')}"}
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Root Cause:*\n{fix.get('root_cause', 'Unknown')}"
                    }
                }
            ]
        }
        
        self.slack.send(json=message)

    def send_error_notification(self, request_data, error):
        """Send error notification"""
        if self.slack:
            self.slack.send(
                json={
                    "text": f"❌ AI Healing failed for run #{request_data['run_id']}: {error}"
                }
            )

    def get_stats(self):
        """Return healing statistics"""
        return self.healing_stats
