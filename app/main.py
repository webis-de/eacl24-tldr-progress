from fastapi import FastAPI, Request, Depends, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, select, and_, or_, desc, func
from sqlalchemy.orm import Session
from app.database.models import Base, Paper, PipelineComponent, Challenge
from typing import List, Optional
import logging
from collections import Counter
import plotly.express as px
import plotly.graph_objects as go

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Database
engine = create_engine("sqlite:///app/database/papers.db")
Base.metadata.bind = engine


def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


@app.get("/")
async def index(request: Request, db: Session = Depends(get_db)):
    # Get all unique values for filters
    papers = db.query(Paper).all()
    venues = sorted(list(set(p.venue for p in papers if p.venue)))
    years = sorted(list(set(p.year for p in papers if p.year)), reverse=True)
    metrics = sorted(list(set(m for p in papers for m in p.metrics if m)))
    datasets = sorted(list(set(d for p in papers for d in p.datasets if d)))
    challenges = sorted(list(set(c.name for p in papers for c in p.challenges)))

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "venues": venues,
            "years": years,
            "metrics": metrics,
            "datasets": datasets,
            "challenges": challenges,
        },
    )


@app.get("/components")
async def components_page(request: Request, db: Session = Depends(get_db)):
    # Get all unique values for filters
    papers = db.query(Paper).order_by(desc(Paper.year)).all()
    components = db.query(PipelineComponent).all()

    # Get component counts using SQLAlchemy relationships
    component_counts = {}
    for paper in papers:
        for component in paper.pipeline_components:
            component_name = component.name
            if component_name not in component_counts:
                component_counts[component_name] = 0
            component_counts[component_name] += 1

    # Include initial papers in the response
    total_papers = len(papers)
    per_page = 10
    total_pages = (total_papers + per_page - 1) // per_page
    papers = papers[:per_page]  # Get first page

    return templates.TemplateResponse(
        "components.html",
        {
            "request": request,
            "component_counts": component_counts,
            "papers": papers,
            "page": 1,
            "total_pages": total_pages,
            "has_next": 1 < total_pages,
            "total_filtered": total_papers,
            "filter_query": "",
        },
    )


@app.get("/api/papers")
async def get_papers(
    request: Request,
    db: Session = Depends(get_db),
    page: int = 1,
    per_page: int = 10,
    venues: str = None,
    years: str = None,
    metrics: str = None,
    datasets: str = None,
    challenges: str = None,
    components: list[str] = Query(None),
    search: str = None,
):
    print(f"\n=== Processing request with components: {components} ===")
    query = select(Paper).order_by(desc(Paper.year))

    filters = []
    filter_params = {}

    if venues:
        venue_list = venues.split(",")
        filters.append(Paper.venue.in_(venue_list))
        filter_params["venues"] = venues

    if years:
        year_list = [int(y) for y in years.split(",")]
        filters.append(Paper.year.in_(year_list))
        filter_params["years"] = years

    if metrics:
        metric_list = metrics.split(",")
        for metric in metric_list:
            filters.append(Paper.metrics.contains(metric))
        filter_params["metrics"] = metrics

    if datasets:
        dataset_list = datasets.split(",")
        for dataset in dataset_list:
            filters.append(Paper.datasets.contains(dataset))
        filter_params["datasets"] = datasets

    if challenges:
        challenge_list = challenges.split(",")
        for challenge in challenge_list:
            filters.append(Paper.challenges.any(Challenge.name == challenge))
        filter_params["challenges"] = challenges

    if components:
        print(f"Creating filters for components: {components}")
        component_filters = []
        for component in components:
            print(f"Adding filter for component: {component}")
            component_filters.append(
                Paper.pipeline_components.any(PipelineComponent.name == component)
            )

        if component_filters:
            filters.append(or_(*component_filters))
            print(f"Added OR filter with {len(component_filters)} conditions")
        filter_params["components"] = ",".join(components)

    if search:
        search_term = f"%{search}%"
        filters.append(
            or_(
                Paper.title.ilike(search_term),
                Paper.abstract.ilike(search_term),
                Paper.tldr.ilike(search_term),
            )
        )
        filter_params["search"] = search

    if filters:
        query = query.filter(and_(*filters))

    # Execute query and get results
    papers = db.execute(query).scalars().all()
    total_papers = len(papers)
    print(f"Query returned {total_papers} papers")

    # Apply pagination
    total_pages = (total_papers + per_page - 1) // per_page
    query = query.offset((page - 1) * per_page).limit(per_page)
    papers = db.execute(query).scalars().all()
    print(f"After pagination: {len(papers)} papers (page {page} of {total_pages})")

    filter_query = "&".join([f"{k}={v}" for k, v in filter_params.items()])
    print(f"Filter query: {filter_query}\n")

    return templates.TemplateResponse(
        "paper_card.html",
        {
            "request": request,
            "papers": papers,
            "page": page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "total_filtered": total_papers,
            "filter_query": filter_query,
        },
    )


@app.get("/api/filters")
async def get_filters(db: Session = Depends(get_db)):
    venues = db.query(Paper.venue).distinct().all()
    years = db.query(Paper.year).distinct().order_by(Paper.year.desc()).all()

    # Get unique metrics and datasets from JSON arrays
    metrics_query = db.query(Paper.metrics).distinct().all()
    datasets_query = db.query(Paper.datasets).distinct().all()

    metrics = set()
    datasets = set()
    for m in metrics_query:
        metrics.update(m[0])
    for d in datasets_query:
        datasets.update(d[0])

    return {
        "venues": [v[0] for v in venues],
        "years": [y[0] for y in years],
        "metrics": list(metrics),
        "datasets": list(datasets),
    }


@app.get("/api/challenges")
async def get_challenges(db: Session = Depends(get_db)):
    challenges = db.query(Challenge).all()
    return [{"name": c.name, "paper_count": len(c.papers)} for c in challenges]


@app.get("/about")
async def about_page(request: Request, db: Session = Depends(get_db)):
    # Get total papers
    total_papers = db.query(Paper).count()

    # Get dataset statistics
    all_datasets = []
    for paper in db.query(Paper).all():
        all_datasets.extend(paper.datasets)
    dataset_counts = Counter(all_datasets)
    top_10_datasets = dict(
        sorted(dataset_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    )

    # Create datasets bar plot
    datasets_fig = go.Figure(
        data=[
            go.Bar(
                x=list(top_10_datasets.values()),
                y=list(top_10_datasets.keys()),
                orientation="h",
            )
        ]
    )
    datasets_fig.update_layout(
        xaxis_title="Number of Papers",
        yaxis_title="Dataset",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
    )

    # Get challenges distribution
    challenges_count = (
        db.query(Challenge.name, func.count(Paper.id))
        .join(Challenge.papers)
        .group_by(Challenge.name)
        .all()
    )
    challenges_dict = {
        name.replace("-", " ").title(): count for name, count in challenges_count
    }

    # Create challenges pie chart
    challenges_fig = px.pie(
        values=list(challenges_dict.values()),
        names=list(challenges_dict.keys()),
    )
    challenges_fig.update_layout(height=400, margin=dict(l=20, r=40, t=40, b=20))

    # Get components distribution
    components_count = (
        db.query(PipelineComponent.name, func.count(Paper.id))
        .join(PipelineComponent.papers)
        .group_by(PipelineComponent.name)
        .all()
    )
    components_dict = dict(components_count)

    # Create components bar plot
    components_fig = go.Figure(
        data=[go.Bar(x=list(components_dict.keys()), y=list(components_dict.values()))]
    )
    components_fig.update_layout(
        xaxis_title="Component",
        yaxis_title="Number of Papers",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_tickangle=-45,
    )

    return templates.TemplateResponse(
        "about.html",
        {
            "request": request,
            "total_papers": total_papers,
            "unique_datasets": len(dataset_counts),
            "total_challenges": len(challenges_dict),
            "total_components": len(components_dict),
            "datasets_plot": datasets_fig.to_html(full_html=False),
            "challenges_plot": challenges_fig.to_html(full_html=False),
            "components_plot": components_fig.to_html(full_html=False),
        },
    )
