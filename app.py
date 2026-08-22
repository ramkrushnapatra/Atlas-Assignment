from flask import Flask, flash, redirect, render_template, request, url_for

from reconciliation.core.canonical import Source, Status
from reconciliation.db import get_session, init_db
from reconciliation.services import (
  accept_orphan, count_status, create_manual_match, get_match, get_run,
  list_files, list_runs, start_run, upload as save_upload,
)

app = Flask(__name__)
app.secret_key = "dev"


@app.before_request
def _init():
  init_db()


def db():
  return get_session()


@app.route("/")
def index():
  s = db()
  try:
    return render_template("index.html", files=list_files(s), runs=list_runs(s))
  finally:
    s.close()


@app.route("/upload", methods=["POST"])
def upload():
  s = db()
  try:
    src = request.form.get("source_type")
    f = request.files.get("file")
    if not f or not src:
      flash("pick a file", "error")
      return redirect(url_for("index"))
    r = save_upload(s, f.filename, f.read().decode(), Source(src), request.form.get("is_correction") == "on")
    flash(r.msg, "success" if r.ok else "warning")
    return redirect(url_for("index"))
  finally:
    s.close()


@app.route("/run", methods=["POST"])
def run_reconciliation():
  s = db()
  try:
    rid = start_run(s)
    flash(f"run #{rid} done", "success")
    return redirect(url_for("run_detail", run_id=rid))
  except Exception as e:
    flash(str(e), "error")
    return redirect(url_for("index"))
  finally:
    s.close()


@app.route("/run/<int:run_id>")
def run_detail(run_id):
  s = db()
  try:
    run = get_run(s, run_id)
    if not run:
      flash("not found", "error")
      return redirect(url_for("index"))
    attention = {Status.DIFF.value, Status.UNMATCHED_L.value, Status.UNMATCHED_S.value}
    return render_template("run_detail.html", run=run, counts=count_status(run),
      needs_attention=[m for m in run.matches if m.status in attention],
      all_matches=sorted(run.matches, key=lambda m: m.status))
  finally:
    s.close()


@app.route("/run/<int:run_id>/match/<int:match_id>")
def match_detail(run_id, match_id):
  s = db()
  try:
    m = get_match(s, match_id)
    if not m or m.run_id != run_id:
      flash("not found", "error")
      return redirect(url_for("run_detail", run_id=run_id))
    return render_template("match_detail.html", run_id=run_id, match=m)
  finally:
    s.close()


@app.route("/run/<int:run_id>/manual-match", methods=["GET", "POST"])
def manual_match(run_id):
  s = db()
  try:
    run = get_run(s, run_id)
    if not run:
      flash("not found", "error")
      return redirect(url_for("index"))

    if request.method == "POST":
      act = request.form.get("action")
      if act == "match":
        lid, sid = request.form.get("ledger_id"), request.form.get("statement_id")
        if lid and sid:
          create_manual_match(s, lid, sid)
          flash(f"matched {lid} ↔ {sid}", "success")
        else:
          flash("pick one from each side", "error")
      elif act == "accept_orphan":
        src, eid = request.form.get("source_system"), request.form.get("external_id")
        if src and eid:
          accept_orphan(s, Source(src), eid)
          flash(f"{eid} accepted as orphan", "success")
      return redirect(url_for("run_detail", run_id=start_run(s)))

    return render_template("manual_match.html", run_id=run_id,
      unmatched_ledger=[m for m in run.matches if m.status == Status.UNMATCHED_L.value],
      unmatched_statement=[m for m in run.matches if m.status == Status.UNMATCHED_S.value])
  finally:
    s.close()


if __name__ == "__main__":
  init_db()
  app.run(debug=True, port=5000)
