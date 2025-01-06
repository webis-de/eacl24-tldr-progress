import pandas as pd
import ast
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.models import Base, Paper, PipelineComponent, Challenge

def parse_list_field(field):
    if pd.isna(field):
        return []
    try:
        # First try ast.literal_eval
        return ast.literal_eval(field)
    except:
        try:
            # If that fails, try json.loads
            return json.loads(field)
        except:
            # If both fail, return empty list
            return []

def parse_dict_field(field):
    if pd.isna(field):
        return {}
    try:
        # First try ast.literal_eval
        return ast.literal_eval(field)
    except:
        try:
            # If that fails, try json.loads
            return json.loads(field)
        except:
            # If both fail, return empty dict
            return {}

def clean_string(s):
    if pd.isna(s):
        return None
    return s.strip() if isinstance(s, str) else s

def init_db():
    # Create SQLite database
    engine = create_engine('sqlite:///app/database/papers.db', echo=True)
    Base.metadata.create_all(engine)
    
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Read CSV file
    df = pd.read_csv('data/all_papers_processed_and_uploaded_learning_corrected.csv')
    
    # Initialize pipeline components
    pipeline_categories = {
        'Document Representation': ['Input Encoding', 'Unit Relationship', 'Data Augmentation', 'External Knowledge'],
        'Model Training': ['Learning Paradigm', 'Objective Function', 'Auxiliary Tasks'],
        'Summary Generation': ['Unit Selection', 'Controlled Generation', 'Post Processing']
    }
    
    component_dict = {}
    for category, components in pipeline_categories.items():
        for comp_name in components:
            component = PipelineComponent(name=comp_name, category=category)
            session.add(component)
            component_dict[comp_name] = component
    
    # Get unique challenges and create Challenge objects
    challenge_dict = {}
    all_challenges = set()
    for challenges in df['challenge_type'].apply(parse_list_field):
        all_challenges.update(challenges)
    
    for challenge_name in all_challenges:
        if challenge_name:  # Skip empty strings
            challenge = Challenge(name=challenge_name)
            session.add(challenge)
            challenge_dict[challenge_name] = challenge
    
    # Create Paper objects
    for _, row in df.iterrows():
        # Print for debugging
        print(f"Processing paper: {row['title']}")
        print(f"Authors before parsing: {row['authors']}")
        authors = parse_list_field(row['authors'])
        print(f"Authors after parsing: {authors}")
        
        paper = Paper(
            id=row['id'],
            title=clean_string(row['title']),
            venue=clean_string(row['venue']),
            year=row['year'],
            authors=authors,
            abstract=clean_string(row['abstract']),
            tldr=clean_string(row['tldr']),
            purpose=parse_dict_field(row['purpose']),
            paper_type=parse_list_field(row['paper_type']),
            datasets=parse_list_field(row['datasets']),
            metrics=parse_list_field(row['metrics']),
            manual_evaluation=parse_list_field(row['manual_evaluation']),
            code_url=clean_string(row['code_url']),
            paper_url=clean_string(row['paper_url']),
            problems_with_solutions=parse_dict_field(row['problems_with_solutions']),
            learning=clean_string(row['learning']),
            domains=parse_list_field(row['domains'])
        )
        
        # Add pipeline components
        components = parse_list_field(row['pipeline_components'])
        for comp_name in components:
            if comp_name in component_dict:
                paper.pipeline_components.append(component_dict[comp_name])
        
        # Add challenges
        challenges = parse_list_field(row['challenge_type'])
        for challenge_name in challenges:
            if challenge_name in challenge_dict:
                paper.challenges.append(challenge_dict[challenge_name])
        
        session.add(paper)
    
    # Commit all changes
    session.commit()
    session.close()

if __name__ == '__main__':
    init_db()
