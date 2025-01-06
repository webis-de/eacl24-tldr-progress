from sqlalchemy import Column, Integer, String, Table, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.sqlite import JSON

Base = declarative_base()

# Association tables for many-to-many relationships
paper_pipeline_components = Table(
    'paper_pipeline_components',
    Base.metadata,
    Column('paper_id', String, ForeignKey('papers.id')),
    Column('component_id', Integer, ForeignKey('pipeline_components.id'))
)

paper_challenges = Table(
    'paper_challenges',
    Base.metadata,
    Column('paper_id', String, ForeignKey('papers.id')),
    Column('challenge_id', Integer, ForeignKey('challenges.id'))
)

class Paper(Base):
    __tablename__ = 'papers'
    
    id = Column(String, primary_key=True)
    title = Column(String)
    venue = Column(String)
    year = Column(Integer)
    authors = Column(JSON)  # Store as JSON array
    abstract = Column(String)
    tldr = Column(String)
    purpose = Column(JSON)  # Store as JSON object
    paper_type = Column(JSON)  # Store as JSON array
    datasets = Column(JSON)  # Store as JSON array
    metrics = Column(JSON)  # Store as JSON array
    manual_evaluation = Column(JSON)  # Store as JSON array
    code_url = Column(String)
    paper_url = Column(String)
    problems_with_solutions = Column(JSON)  # Store as JSON object
    learning = Column(String)
    domains = Column(JSON)  # Store as JSON array
    
    # Relationships
    pipeline_components = relationship('PipelineComponent', secondary=paper_pipeline_components, back_populates='papers')
    challenges = relationship('Challenge', secondary=paper_challenges, back_populates='papers')

class PipelineComponent(Base):
    __tablename__ = 'pipeline_components'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    category = Column(String)  # Document Representation, Model Training, or Summary Generation
    
    # Relationships
    papers = relationship('Paper', secondary=paper_pipeline_components, back_populates='pipeline_components')

class Challenge(Base):
    __tablename__ = 'challenges'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    
    # Relationships
    papers = relationship('Paper', secondary=paper_challenges, back_populates='challenges')
