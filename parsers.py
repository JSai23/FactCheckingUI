from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import ast
import json
import re
import pandas as pd

@dataclass
class KeyFinding:
    type: str
    description: str

@dataclass
class RecommendedAction:
    action: str
    rationale: str

@dataclass
class PostFindings:
    findings: List[KeyFinding]

@dataclass
class FactCheckerRecommendations:
    recommendations: List[RecommendedAction]

@dataclass
class PresentationData:
    title: str
    key_findings: PostFindings
    recommended_actions: FactCheckerRecommendations
    process: str
    status: str
    message: Optional[str] = None

    @classmethod
    def parse_from_string(cls, data_str: str) -> 'PresentationData':
        # Extract title using backreference so we match until the same quote character
        title_match = re.search(r"title=(['\"])(.*?)\1", data_str)
        title = title_match.group(2) if title_match else ""

        # Extract key findings (support single or double quotes)
        findings_str = re.search(r'key_findings=PostFindings\(findings=\[(.*?)\]\)', data_str)
        findings = []
        if findings_str:
            keyfinding_pattern = r"KeyFinding\(type=(['\"])(.*?)\1, description=(['\"])(.*?)\3\)"
            for item in re.finditer(keyfinding_pattern, findings_str.group(1)):
                findings.append(KeyFinding(type=item.group(2), description=item.group(4)))

        # Extract recommended actions
        actions_str = re.search(r'recommended_actions=FactCheckerRecommendations\(recommendations=\[(.*?)\]\)', data_str)
        actions = []
        if actions_str:
            action_pattern = r"RecommendedAction\(action=(['\"])(.*?)\1, rationale=(['\"])(.*?)\3"
            for item in re.finditer(action_pattern, actions_str.group(1)):
                actions.append(RecommendedAction(action=item.group(2), rationale=item.group(4)))

        # Extract process and status
        process_match = re.search(r"process='([^']*)'", data_str)
        status_match = re.search(r"status='([^']*)'", data_str)
        message_match = re.search(r"message=(None|'[^']*')", data_str)

        return cls(
            title=title,
            key_findings=PostFindings(findings=findings),
            recommended_actions=FactCheckerRecommendations(recommendations=actions),
            process=process_match.group(1) if process_match else "",
            status=status_match.group(1) if status_match else "",
            message=None if not message_match or message_match.group(1) == 'None' 
                   else message_match.group(1).strip("'")
        )

@dataclass
class PostData:
    post_id: str
    text: str
    # Legacy alias (no default to keep dataclass field ordering constraints)
    post_text: str
    user_name: str
    user_handle: str
    user_verified: bool
    user_location: str
    user_description: str
    user_followers_count: int
    user_following_count: int
    user_statuses_count: int
    user_created_at: str
    post_created_at: str
    repost_count: int
    reply_count: int
    like_count: int
    quote_count: int
    impression_count: int
    bookmark_count: int
    priority_score: float
    engagement_score: float
    amplifiability_score: float
    urgency_score: float
    top_claims: List[str]
    emotional_tone: str
    is_checkworthy: bool
    has_checkworthy_claims: bool = False
    
    @classmethod
    def parse_from_dict(cls, data: Dict[str, Any]) -> 'PostData':
        # Initialize with default values
        default_data = {
            'post_id': '',
            'text': '',
            'post_text': '',
            'user_name': '',
            'user_handle': '',
            'user_verified': False,
            'user_location': '',
            'user_description': '',
            'user_followers_count': 0,
            'user_following_count': 0,
            'user_statuses_count': 0,
            'user_created_at': '',
            'post_created_at': '',
            'repost_count': 0,
            'reply_count': 0,
            'like_count': 0,
            'quote_count': 0,
            'impression_count': 0,
            'bookmark_count': 0,
            'priority_score': 0.0,
            'engagement_score': 0.0,
            'amplifiability_score': 0.0,
            'urgency_score': 0.0,
            'top_claims': [],
            'emotional_tone': '',
            'is_checkworthy': False,
            'has_checkworthy_claims': False
        }
        
        # Update with provided data
        for key, value in data.items():
            if key in default_data:
                # Handle special cases
                if key == 'top_claims':
                    if isinstance(value, list):
                        default_data[key] = value
                    elif isinstance(value, str):
                        try:
                            # Try to parse as JSON
                            default_data[key] = json.loads(value)
                        except:
                            try:
                                # Try to parse as literal
                                default_data[key] = ast.literal_eval(value)
                            except:
                                # If all else fails, treat as single item
                                default_data[key] = [value] if value else []
                    else:
                        default_data[key] = []
                elif key in ['priority_score', 'engagement_score', 'amplifiability_score', 'urgency_score']:
                    try:
                        default_data[key] = float(value) if value is not None else 0.0
                    except:
                        default_data[key] = 0.0
                elif key in ['user_followers_count', 'user_following_count', 'user_statuses_count',
                           'repost_count', 'reply_count', 'like_count', 'quote_count',
                           'impression_count', 'bookmark_count']:
                    try:
                        default_data[key] = int(float(value)) if value is not None else 0
                    except:
                        default_data[key] = 0
                elif key == 'user_verified':
                    if isinstance(value, bool):
                        default_data[key] = value
                    elif isinstance(value, str):
                        default_data[key] = value.lower() == 'true'
                    else:
                        default_data[key] = bool(value)
                elif key == 'is_checkworthy':
                    if isinstance(value, bool):
                        default_data[key] = value
                    elif isinstance(value, str):
                        default_data[key] = value.lower() == 'true'
                    else:
                        default_data[key] = bool(value)
                else:
                    default_data[key] = str(value) if value is not None else ''
        
        # Ensure legacy alias synchronisation
        if default_data.get('post_text') and not default_data.get('text'):
            default_data['text'] = default_data['post_text']
        elif default_data.get('text') and not default_data.get('post_text'):
            default_data['post_text'] = default_data['text']
        
        return cls(**default_data)

def parse_display_output(file_path: str) -> List[tuple[PresentationData, PostData]]:
    """Parse the display_output.csv file and return a list of tuples containing presentation and post data"""
    try:
        # Read CSV with custom quoting to handle nested quotes
        df = pd.read_csv(file_path)
        parsed_data = []
        
        for idx, row in df.iterrows():
            try:
                # NOTE: In the CSV the columns are swapped – the column labelled "post" actually
                # contains the presentation string and vice-versa.  Swap them here so that the
                # parser receives the expected inputs.

                presentation_str = str(row['post']).strip()
                post_str = str(row['presentation']).strip()

                # Parse presentation data
                presentation = PresentationData.parse_from_string(presentation_str)
                
                # Replace numpy float64 references with regular floats
                post_str = re.sub(r'np\.float64\(([\d.]+)\)', r'\1', post_str)

                # Standardise special literals for ast parsing
                ast_safe_post_str = (post_str
                                      .replace('nan', 'None')
                                      .replace('False', 'False')
                                      .replace('True', 'True'))

                # Attempt to parse with ast.literal_eval which supports Python style dict/str
                post_dict = None
                try:
                    post_dict = ast.literal_eval(ast_safe_post_str)
                except Exception:
                    # Fallback to JSON: need to convert to JSON-compatible string
                    json_safe_post_str = post_str.replace('nan', 'null')
                    # crude conversion of single quotes to double quotes while preserving
                    # interior apostrophes by using regex for keys and simple literals.
                    def single_to_double_quotes(s: str) -> str:
                        # Replace keys and string literals enclosed in single quotes with double quotes
                        return re.sub(r"'([^']*)'", lambda m: '"' + m.group(1).replace('"', '\\"') + '"', s)
                    try:
                        post_dict = json.loads(single_to_double_quotes(json_safe_post_str))
                    except Exception:
                        print(f"Failed to parse post data for row {idx}")
                        continue
                
                # Clean up the dictionary
                if 'priority_score_breakdown' in post_dict:
                    del post_dict['priority_score_breakdown']
                
                # Convert any remaining numpy values to Python types
                for key, value in post_dict.items():
                    if isinstance(value, str) and value.startswith('np.'):
                        try:
                            post_dict[key] = float(re.search(r'\(([\d.]+)\)', value).group(1))
                        except:
                            post_dict[key] = 0.0
                
                # Use dataclass parser for base fields
                post = PostData.parse_from_dict(post_dict)

                # Attach any additional fields that the dataclass might not yet define so that the
                # Streamlit UI does not break when trying to access them.
                for k, v in post_dict.items():
                    if not hasattr(post, k):
                        # Attempt a lightweight normalisation for numeric looking values stored as
                        # strings
                        if isinstance(v, str):
                            # Clean common numeric strings (e.g. '338.0', '0.0', 'False')
                            if v.replace('.', '', 1).isdigit():
                                try:
                                    v_conv = int(float(v))
                                except:
                                    v_conv = v
                                v = v_conv
                            elif v.lower() in ['false', 'true']:
                                v = v.lower() == 'true'
                        setattr(post, k, v)

                parsed_data.append((presentation, post))
            except Exception as e:
                print(f"Error parsing row {idx}: {str(e)}")
                continue
        
        if not parsed_data:
            print("Warning: No data was successfully parsed from the CSV file")
        else:
            print(f"Successfully parsed {len(parsed_data)} rows")
        
        return parsed_data
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")
        return [] 