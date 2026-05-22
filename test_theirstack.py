from app import create_app
app = create_app()
with app.app_context():
    from engines.job_market_engine import fetch_job_pulse

    for title in ["AI Engineer", "Data Analyst", "Cybersecurity Analyst"]:
        print(f"\n--- {title} ---")
        result = fetch_job_pulse(title)
        if result:
            print(f"  total_jobs  : {result['total_jobs']:,}")
            print(f"  remote_pct  : {result['remote_pct']}%")
            print(f"  seniority   : {result['seniority']}")
            print(f"  demand      : {result['demand_label']} ({result['demand_color']})")
            print(f"  top_skills  : {[s['label'] for s in result['top_skills']]}")
            print(f"  companies   : {[c['name'] for c in result['companies']]}")
            print(f"  avg_salary  : {result['avg_salary_usd']}")
        else:
            print("  No data returned")
