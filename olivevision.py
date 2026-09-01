"""OliveVision operational CLI and optional local Tk GUI."""
from __future__ import annotations
import argparse
import json
import sys
import time
import threading
import traceback
from pathlib import Path
from collections import deque

import cv2
import numpy as np
from src.runtime import (Analyzer, Store, VideoAnalyzer, build_logger, capture_camera,
                         explain_detection, load_runtime_config, save_observation,
                         analyze_health_trend, integrate_soil_moisture,
                         _frame_position, _fruit_why,
                         FRUIT_SIGNAL_THRESHOLDS, DEFAULTS as DEFAULTS_REF)
from src.soil_moisture import (SoilMoistureClient, get_moisture_for_olive_analysis,
                               format_moisture_report, get_moisture_status,
                               assess_moisture_health)
from src.cli_ui import (Spinner, ProgressBar, panel, bold, dim, cyan,
                        green, yellow, red, accent_ok, accent_warn, accent_err,
                        countup_line)

ROOT = Path(__file__).resolve().parent

def _error(msg, hint=None, details=None):
    """Structured error output for the CLI."""
    parts = [f"{accent_err('ERROR')}  {msg}"]
    if hint:
        parts.append(f"{dim('HINT')}  {hint}")
    if details:
        parts.append(f"{dim('DETAIL')}  {details}")
    raise SystemExit("\n".join(parts))

def resources(args):
    config = load_runtime_config(args.config)
    drone = getattr(args, "drone", False)
    upscale = getattr(args, "upscale", False)
    upscaler = None
    if upscale:
        from src.upscale import ImageUpscaler
        try:
            upscaler = ImageUpscaler(
                model=getattr(args, "upscale_model", "realesrgan-x4plus"),
                scale=getattr(args, "upscale_scale", 2),
                threshold=getattr(args, "upscale_threshold", 900),
            )
        except Exception:
            upscaler = None
    analyzer = Analyzer(config, resolution_mode="auto", drone_mode=drone,
                        upscaler=upscaler, upscale=upscale)
    return analyzer, Store(args.database), config

def show(result):
    clean = {k: v for k, v in result.items() if not isinstance(v, np.ndarray)}
    print(json.dumps(clean, ensure_ascii=False, indent=2))

def _print_summary(result):
    """Human-friendly one-line summary of an observation."""
    leaves = result.get("leaf_count", 0)
    fruits = result.get("fruit_count", 0)
    green_cov = float(result.get("green_coverage", 0.0))
    stage = result.get("leaf_color_stage", "?")
    mat = result.get("fruit_maturity", "?")
    wr = result.get("wrinkled_fruit_count", 0)
    print(f"  {bold('Leaves')}   {leaves}")
    print(f"  {bold('Fruits')}   {fruits}" + (f"  ({accent_warn(str(wr))} wrinkled)" if wr else ""))
    print(f"  {bold('Green')}    {green_cov:.1f}%  (leaf stage: {stage})")
    print(f"  {bold('Maturity')} {mat}")

def _print_soil_health(health):
    """Print soil moisture health assessment."""
    risk = health.get("moisture_risk", "unknown")
    msg = health.get("moisture_message", "")
    combined = health.get("combined_health_score", 0.5)
    visual = health.get("visual_health_score", 0.5)
    moisture = health.get("moisture_health_score", 0.5)
    weight = health.get("moisture_weight", 0.0)
    if risk == "unknown":
        return
    parts = []
    parts.append(f"  {bold('Soil')}     {_risk_color(risk)}  {dim(msg)}")
    parts.append(f"  {bold('Scores')}   visual={visual:.2f}  moisture={moisture:.2f}  "
                 f"combined={green(f'{combined:.2f}') if combined >= 0.6 else yellow(f'{combined:.2f}')}"
                 f"  (weight={weight:.0%})")
    print("\n".join(parts))


def _print_verdict(result):
    """Colour-coded health verdict drawn from the result."""
    fruits = result.get("fruit_count", 0)
    green_cov = float(result.get("green_coverage", 0.0))
    wr = result.get("wrinkled_fruit_count", 0)
    if fruits == 0:
        verdict, fn = "No fruit detected this time", accent_warn
    elif wr / max(1, fruits) >= 0.5:
        verdict, fn = f"{wr}/{fruits} fruits look dehydrated / wrinkled", accent_warn
    elif green_cov < 5:
        verdict, fn = "Very little foliage visible", accent_warn
    else:
        verdict, fn = f"{fruits} fruit(s) healthy-looking and visible", accent_ok
    print(f"  {bold('Verdict')}  {fn(verdict)}")

def explain(args, result):
    print()
    print(cli_explain(result))

def _conf_color(conf):
    if conf >= 0.7:
        return accent_ok
    if conf >= 0.55:
        return cyan
    return yellow

def _maturity_color(maturity):
    m = str(maturity).lower()
    if "ripe" in m or "yellow" in m:
        return yellow
    if "red" in m or "dark" in m or "over" in m:
        return accent_warn
    return green

def _wrinkle_color(wrinkle):
    w = str(wrinkle).lower()
    if "heavily" in w:
        return accent_err
    if "slightly" in w:
        return accent_warn
    return green

def cli_explain(result):
    """Colourful, structured CLI explanation (ANSI, for terminals only)."""
    mode = result.get("detect_mode", "multi_signal")
    w, h = result.get("image_width", "?"), result.get("image_height", "?")
    blur = float(result.get("blur_level", 0.0))
    blur_score = float(result.get("blur_score", 0.0))
    out = []
    out.append(panel(f"Detection report ({mode} pipeline)", ""))
    out.append(f"  image        {dim(f'{w}x{h}px')}")
    if blur >= 0.75:
        focus = accent_err(f"very blurry (variance {blur_score:.0f}) — deblurred")
    elif blur >= 0.4:
        focus = accent_warn(f"moderately blurry (variance {blur_score:.0f})")
    else:
        focus = accent_ok(f"sharp (variance {blur_score:.0f})")
    out.append(f"  focus        {focus}")
    out.append("")

    def _objects(kind, objects, count):
        block = []
        title = kind
        if not objects:
            block.append(f"  {dim('no ' + title.lower() + ' detected')}")
            return block
        for i, obj in enumerate(objects, start=1):
            conf = float(obj.get("confidence", 0.0))
            cx = obj.get("center_x", 0)
            cy = obj.get("center_y", 0)
            where = f"({cx:.0f},{cy:.0f})" if cx or cy else "(-,-)  "
            tag = f"{kind[0].upper()}#{i}"
            line = (f"  {bold(f'{tag:>4}')}  {dim('@')} {cyan(where):>14}  "
                    f"{_conf_color(conf)(f'{conf * 100:4.0f}%')}")
            if kind == "fruits":
                maturity = obj.get("maturity") or "?"
                wrinkle = obj.get("wrinkle_label") or "smooth"
                line += f"  {_maturity_color(maturity)(maturity):>12}" \
                        f"  wrinkle {_wrinkle_color(wrinkle)(wrinkle):>14}"
                if obj.get("low_signal"):
                    line += f"  {accent_err('LOW-SIGNAL')}"
            block.append(line)
            if kind == "fruits":
                where_zone = _frame_position(obj, result.get("image_width", 0),
                                             result.get("image_height", 0))
                block.append(f"  {'':>4}  {dim('where:')} {cyan(where_zone)}")
                for why in _fruit_why(obj, result.get("fruit_thresholds") or {},
                                      result.get("signal_thresholds") or FRUIT_SIGNAL_THRESHOLDS):
                    block.append(f"  {'':>4}  {dim('why:')} {why}")
            else:
                signals = obj.get("detect_evidence") or []
                ratios = obj.get("signal_ratios") or {}
                if signals:
                    sig = ", ".join(bold(s) for s in signals)
                    block.append(f"  {'':>4}  {dim('evidence:')} {sig}")
                if ratios:
                    parts = []
                    for label, key in (("y/g", "yellow_green"), ("ripe", "ripe"),
                                       ("dark", "dark"), ("circle", "hough_circle")):
                        v = ratios.get(key, 0)
                        col = accent_ok if v > 0.2 else dim
                        parts.append(f"{label}{col(f'{v:.2f}')}")
                    block.append(f"  {'':>4}  {dim('signals:')} {' '.join(parts)}")
        return block

    leaves = result.get("leaf_objects", [])
    fruits = result.get("fruit_objects", [])
    out.append(panel(f"Leaves ({len(leaves)})", "\n".join(_objects("leaves", leaves, 0))))
    out.append("")
    out.append(panel(f"Fruits ({len(fruits)})", "\n".join(_objects("fruits", fruits, 0))))

    gcov = float(result.get("green_coverage", 0.0))
    stage = result.get("leaf_color_stage", "?")
    mat = result.get("fruit_maturity", "?")
    wrinkle_sum = result.get("fruit_wrinkle_summary") or {}
    maturity_brk = result.get("fruit_maturity_breakdown") or {}
    lines = [f"  {bold('Green coverage')}  {_conf_color(gcov / 100)(f'{gcov:.1f}%')}"
             f"   leaf stage {cyan(str(stage))}",
             f"  {bold('Maturity')}       {_maturity_color(mat)(str(mat))}"]
    if maturity_brk:
        parts = ", ".join(f"{bold(str(v))} {k}" for k, v in sorted(maturity_brk.items()) if v > 0)
        lines.append(f"  {bold('by colour')}      {dim(parts)}")
    if wrinkle_sum:
        parts = ", ".join(f"{_wrinkle_color(k)(str(v))} {k}" for k, v in wrinkle_sum.items() if v > 0)
        lines.append(f"  {bold('wrinkled')}       {parts}")
    out.append("")
    out.append(panel("Summary", "\n".join(lines)))
    # Pipeline diagnostics: what got rejected and how strong each signal was.
    diag = result.get("pipeline_diagnostics") or {}
    if diag:
        rows = []
        for cls in ("leaves", "fruits"):
            d = diag.get(cls) or {}
            cand = d.get("candidates", 0)
            acc = d.get("accepted", 0)
            rej = d.get("rejected", 0)
            rows.append(f"  {bold(cls.capitalize()):>8}  {dim(f'{cand} candidates')} -> "
                        f"{green(str(acc) + ' kept')}")
            rej_by = d.get("rejected_by") or {}
            if rej_by:
                parts = ", ".join(f"{dim(k)}={red(str(v))}"
                                  for k, v in sorted(rej_by.items(), key=lambda kv: -kv[1]))
                rows.append(f"  {'':>8}  {dim('rejected:')} {parts}")
        out.append("")
        out.append(panel("Pipeline diagnostics", "\n".join(rows)))
    return "\n".join(out)

def show_diag(result):
    """Colourful summary of pipeline rejection reasons (CLI only)."""
    diag = result.get("pipeline_diagnostics") or {}
    if not diag:
        print(dim("No pipeline diagnostics recorded."))
        return
    print(panel("Pipeline diagnostics", "\n".join(_diag_rows(diag))))

def _diag_rows(diag):
    rows = []
    for cls in ("leaves", "fruits"):
        d = diag.get(cls) or {}
        cand = d.get("candidates", 0)
        acc = d.get("accepted", 0)
        rej = d.get("rejected", 0)
        rows.append(f"  {bold(cls.capitalize()):>8}  {dim(f'{cand} candidates')} -> "
                    f"{green(str(acc) + ' kept')}  {red(str(rej) + ' rejected')}")
        rej_by = d.get("rejected_by") or {}
        if rej_by:
            parts = ", ".join(f"{dim(k)}={red(str(v))}"
                              for k, v in sorted(rej_by.items(), key=lambda kv: -kv[1]))
            rows.append(f"  {'':>8}  {dim('rejected:')} {parts}")
    signals = diag.get("signals") or {}
    if signals:
        rows.append(f"  {bold('Signals')}")
        for label, key in (("yellow-green", "yellow_green_mask"), ("ripe", "ripe_mask"),
                           ("dark", "dark_mask"), ("hough circle", "hough_circle_mask")):
            cov = signals.get(key) or {}
            col = accent_ok if cov.get("pct", 0) > 5 else dim
            rows.append(f"  {'':>8}  {cyan(label + ':'):>20} {col(str(cov.get('pct', 0)) + '%')}")
    rows.append(f"  {bold('Accepted fruit mask')}: "
                f"{cyan(str(diag.get('accepted_fruit_mask_pct', 0))) + '% of frame'}")
    return rows

def analyze_file(args):
    logger = build_logger(args.verbose)
    analyzer, store, _ = resources(args)
    path = Path(args.image)
    if not path.exists():
        _error(f"Image not found: {path}",
               hint=f"Check the path. Current directory: {Path.cwd()}")
    if not path.is_file():
        _error(f"Path is not a file: {path}",
               hint="Provide a path to an image file, not a directory")
    logger.info("Reading %s", path)
    with Spinner(f"analysing {path.name}", sys.stderr):
        image = cv2.imread(str(path))
        if image is None:
            _error(f"Failed to read image: {path.name}",
                   hint="File may be corrupt or in an unsupported format (use .jpg/.png)")
        logger.info("Analysing %dx%d image", image.shape[1], image.shape[0])
        result, output = save_observation(analyzer, store, image, "file",
                                          args.output, str(path))
        logger.info("Saved annotation: %s", output)
        logger.info("Stored observation in %s", args.database)
    if not getattr(args, "no_soil_moisture", False):
        try:
            from datetime import datetime as _dt
            obs_time = _dt.fromisoformat(result.get("observed_at", ""))
            soil_data = get_moisture_for_olive_analysis(target_time=obs_time)
            result = integrate_soil_moisture(result, soil_data)
            logger.info("Integrated soil moisture data")
        except Exception as exc:
            logger.info("Soil moisture integration skipped: %s", exc)
    _animate_counts(result)
    print(panel(f"Analysis of {path.name}",
                _print_summary_body(result)))
    _print_verdict(result)
    if result.get("health_assessment"):
        _print_soil_health(result["health_assessment"])
    if args.explain:
        explain(args, result)
    if args.diag:
        show_diag(args, result)
    show(result) if args.verbose else None

def _animate_counts(result):
    """Flash the headline leaf/fruit/green metrics on a single line."""
    leaves = result.get("leaf_count", 0)
    fruits = result.get("fruit_count", 0)
    gcov = float(result.get("green_coverage", 0.0))
    countup_line([
        (lambda: leaves, lambda v: f"{bold('Leaves')} {v:>3.0f}", cyan),
        (lambda: fruits, lambda v: f"{bold('Fruits')} {v:>3.0f}", green),
        (lambda: gcov, lambda v: f"{bold('Green')} {v:>4.1f}%", yellow),
    ])

def _print_summary_body(result):
    """Build the summary body as a string so it can be placed in a panel."""
    lines = []
    leaves = result.get("leaf_count", 0)
    fruits = result.get("fruit_count", 0)
    green_cov = float(result.get("green_coverage", 0.0))
    stage = result.get("leaf_color_stage", "?")
    mat = result.get("fruit_maturity", "?")
    wr = result.get("wrinkled_fruit_count", 0)
    res_mode = result.get("resolution_mode", "normal")
    res_scale = result.get("resolution_scale", 1.0)
    w = result.get("image_width", "?")
    h = result.get("image_height", "?")
    lines.append(f"  {bold('Leaves')}   {leaves}")
    fruits_line = f"  {bold('Fruits')}   {fruits}"
    if wr:
        fruits_line += f"   ({accent_warn(str(wr))} wrinkled)"
    lines.append(fruits_line)
    lines.append(f"  {bold('Green')}    {green_cov:.1f}%   (leaf stage: {stage})")
    lines.append(f"  {bold('Maturity')} {mat}")
    if res_mode != "normal":
        lines.append(f"  {bold('Resolution')} {w}x{h}  mode={cyan(res_mode)}  scale={res_scale}")
    else:
        lines.append(f"  {bold('Resolution')} {w}x{h}")
    return "\n".join(lines)

def _cli_diagnostics_text(result):
    """Plain-text pipeline diagnostics for the GUI Diagnostics tab (no ANSI)."""
    diag = result.get("pipeline_diagnostics") or {}
    lines = []
    lines.append("PIPELINE DIAGNOSTICS")
    lines.append("=" * 60)
    for cls in ("leaves", "fruits"):
        d = diag.get(cls) or {}
        cand = d.get("candidates", 0)
        acc = d.get("accepted", 0)
        rej = d.get("rejected", 0)
        lines.append(f"{cls.capitalize()}: {cand} candidate(s) -> {acc} kept, {rej} rejected")
        rej_by = d.get("rejected_by") or {}
        for k, v in sorted(rej_by.items(), key=lambda kv: -kv[1]):
            lines.append(f"   - rejected by {k}: {v}")
    signals = diag.get("signals") or {}
    if signals:
        lines.append("Colour-signal mask coverage:")
        for label, key in (("yellow-green", "yellow_green_mask"), ("ripe", "ripe_mask"),
                           ("dark", "dark_mask"), ("hough circle", "hough_circle_mask")):
            cov = signals.get(key) or {}
            lines.append(f"   - {label:<14} {cov.get('pixels', 0):>7}px  "
                         f"({cov.get('pct', 0):.2f}%)")
    lines.append(f"Accepted fruit mask coverage: "
                 f"{diag.get('accepted_fruit_mask_pct', 0):.2f}% of frame")
    return "\n".join(lines)

def capture(args):
    logger = build_logger(args.verbose)
    analyzer, store, config = resources(args)
    logger.info("Opening camera %d", args.camera)
    try:
        with Spinner("capturing from camera", sys.stderr):
            image = capture_camera(args.camera, config["runtime"]["camera_warmup_frames"])
            logger.info("Captured %dx%d frame; analysing", image.shape[1], image.shape[0])
            result, output = save_observation(analyzer, store, image,
                                              f"camera:{args.camera}", args.output)
            logger.info("Saved annotation: %s", output)
    except Exception as exc:
        _error(f"Camera {args.camera} failed: {exc}",
               hint="Check that the camera is connected and not in use by another app. "
                    "Try --camera 1 for the second camera.")
    if not getattr(args, "no_soil_moisture", False):
        try:
            from datetime import datetime as _dt
            obs_time = _dt.fromisoformat(result.get("observed_at", ""))
            soil_data = get_moisture_for_olive_analysis(target_time=obs_time)
            result = integrate_soil_moisture(result, soil_data)
            logger.info("Integrated soil moisture data")
        except Exception as exc:
            logger.info("Soil moisture integration skipped: %s", exc)
    print(panel(f"Capture from camera {args.camera}",
                _print_summary_body(result)))
    _print_verdict(result)
    if result.get("health_assessment"):
        _print_soil_health(result["health_assessment"])
    if args.explain:
        explain(args, result)
    if args.diag:
        show_diag(result)

def monitor(args):
    logger = build_logger(args.verbose)
    analyzer, store, config = resources(args)
    interval = args.interval
    cam = args.camera
    tree_id = getattr(args, "tree", None)
    limit = getattr(args, "limit", 0) or 999999
    # Header
    hdr_parts = [f"  {bold('Camera')}   {cyan(str(cam))}",
                 f"  {bold('Interval')} {cyan(str(interval) + 's')}",
                 f"  {bold('Mode')}     {'experiment' if hasattr(args, 'mode') and args.mode == 'experiment' else 'single-shot'}"]
    if tree_id:
        hdr_parts.append(f"  {bold('Tree')}     {cyan(tree_id)}")
    hdr_parts.append(f"  {bold('Limit')}    {limit} cycles" if limit < 999999 else "")
    hdr_parts.append(f"  {bold('DB')}       {dim(str(Path(args.database).name))}")
    print(panel("Monitor started", "\n".join(p for p in hdr_parts if p)))
    print(f"  Press {bold('Ctrl+C')} to stop and see summary.\n")
    print(f"  {'#':>4}  {'Time':>8}  {'L':>3}  {'F':>3}  {'Green':>6}  {'Tree':>12}  {'Output'}")
    print(f"  {dim(chr(9472)*4)}  {dim(chr(9472)*8)}  {dim(chr(9472)*3)}  {dim(chr(9472)*3)}  {dim(chr(9472)*6)}  {dim(chr(9472)*12)}  {dim(chr(9472)*20)}")
    cycle = 0
    results = []
    start_time = time.time()
    try:
        while cycle < limit:
            cycle += 1
            try:
                t0 = time.time()
                with Spinner(f"cycle {cycle}: capturing", sys.stderr):
                    image = capture_camera(cam, config["runtime"]["camera_warmup_frames"])
                    # Inject tree_id into the analysis if provided.
                    result, output = save_observation(analyzer, store, image,
                                                      f"camera:{cam}", args.output)
                    if tree_id:
                        result["tree_id"] = tree_id
                        # Update the stored record with tree_id.
                        if store is not None:
                            con = store._connect()
                            try:
                                con.execute("UPDATE observations SET tree_id = ? "
                                            "WHERE rowid = (SELECT MAX(rowid) FROM observations)",
                                            (tree_id,))
                                con.commit()
                            finally:
                                con.close()
                elapsed = time.time() - t0
                ts = time.strftime("%H:%M:%S")
                gc = result["green_coverage"]
                lvs = result["leaf_count"]
                fts = result["fruit_count"]
                wr = result.get("wrinkled_fruit_count", 0)
                tree_tag = cyan(tree_id[:10]) if tree_id else dim("—")
                row = {"cycle": cycle, "leaves": lvs, "fruits": fts, "green": gc,
                       "wrinkled": wr, "tree_id": tree_id, "elapsed": elapsed}
                results.append(row)
                # Colour-code green coverage
                gc_col = green(f"{gc:>5.1f}%") if gc >= 20 else (yellow(f"{gc:>5.1f}%") if gc >= 10 else red(f"{gc:>5.1f}%"))
                wr_tag = f"  {red(str(wr) + 'w')}" if wr else ""
                print(f"  {cyan(str(cycle)):>4}  {dim(ts):>8}  {cyan(str(lvs)):>3}  "
                      f"{green(str(fts)):>3}  {gc_col}  {tree_tag:>12}  {dim(str(output.name))}{wr_tag}")
                logger.info("Cycle %d: L=%d F=%d G=%.1f%% elapsed=%.1fs (%s)",
                            cycle, lvs, fts, gc, elapsed, output)
            except Exception as exc:
                ts = time.strftime("%H:%M:%S")
                print(f"  {red(str(cycle)):>4}  {dim(ts):>8}  {red('ERR'):>3}  "
                      f"{dim(type(exc).__name__ + ': ' + str(exc)[:60])}")
                logger.exception("Cycle %d failed: %s", cycle, exc)
            # Countdown to next capture (unless last cycle).
            if cycle < limit and interval > 0:
                next_t = time.strftime("%H:%M:%S", time.localtime(time.time() + interval))
                sys.stderr.write(f"\r{dim(f'Next capture at {next_t}  ({interval}s)')} ")
                sys.stderr.flush()
                time.sleep(interval)
                sys.stderr.write("\r" + " " * 60 + "\r")
                sys.stderr.flush()
    except KeyboardInterrupt:
        pass
    # Summary
    elapsed_total = time.time() - start_time
    print()
    if results:
        n = len(results)
        lvs_avg = sum(r["leaves"] for r in results) / n
        fts_avg = sum(r["fruits"] for r in results) / n
        gc_avg = sum(r["green"] for r in results) / n
        wr_total = sum(r["wrinkled"] for r in results)
        lvs_min = min(r["leaves"] for r in results)
        lvs_max = max(r["leaves"] for r in results)
        fts_min = min(r["fruits"] for r in results)
        fts_max = max(r["fruits"] for r in results)
        body = (f"  {bold('Cycles')}    {n} completed  ({dim(f'{elapsed_total:.0f}s total')})\n"
                f"  {bold('Leaf')}      avg {cyan(str(round(lvs_avg)))}  (min {lvs_min} / max {lvs_max})\n"
                f"  {bold('Fruit')}      avg {green(str(round(fts_avg)))}  (min {fts_min} / max {fts_max})"
                + (f"  {red(str(wr_total) + ' wrinkled total')}" if wr_total else "") + "\n"
                f"  {bold('Green')}      avg {yellow(f'{gc_avg:.1f}%')}")
        print(panel("Monitor summary", body))
    else:
        print(f"  {dim('No successful captures.')}")
    logger.info("Monitor stopped after %d cycle(s).", cycle)

def status(args):
    db_path = Path(args.database)
    if not db_path.exists():
        _error(f"Database not found: {db_path}",
               hint="Run 'analyze' or 'capture' first to create the database.")
    store = Store(args.database)
    if args.tree:
        rows = store.recent_by_tree(args.tree, args.limit)
        title = f"Observations for {args.tree}"
    else:
        rows = store.recent(args.limit)
        title = "Recent observations"
    # Count by source
    src_counts = {}
    for r in rows:
        s = r.get("source", "?")
        src_counts[s] = src_counts.get(s, 0) + 1
    src_parts = "  ".join(f"{cyan(s)}:{v}" for s, v in sorted(src_counts.items()))
    header = f"  {bold('Rows')}   {bold(str(len(rows)))} shown"
    if src_parts:
        header += f"    {dim(src_parts)}"
    print(panel(title, header))
    if not rows:
        print("  No observations yet.")
        return
    for row in rows:
        gc = row["green_coverage"]
        tid = row.get("tree_id", "")
        src = row["source"]
        if src.startswith("video"):
            src_badge = yellow(f"{'VID':>5}")
        elif src.startswith("camera"):
            src_badge = cyan(f"{'CAM':>5}")
        else:
            src_badge = green(f"{'IMG':>5}")
        dt = row["observed_at"][:16].replace("T", " ")
        tree_tag = f" {cyan(tid):>12}" if tid else ""
        lvs = row["leaf_count"]
        fts = row["fruit_count"]
        grn = gc
        sm = row.get("soil_moisture", "")
        sm_tag = ""
        if isinstance(sm, dict) and sm.get("available"):
            sm_status = sm.get("status", "")
            sm_avg = sm.get("average_percent")
            if sm_status and sm_avg is not None:
                sm_tag = f"  {_moisture_badge(sm_status)}={green(f'{sm_avg:.0f}%')}"
        print(f"  {dim(dt)}  {src_badge}{tree_tag}  "
              f"L={cyan(str(lvs).rjust(3))}  F={green(str(fts).rjust(3))}  "
              f"G={yellow(f'{grn:.1f}%')}{sm_tag}")

def export(args):
    csv_path = Path(args.csv)
    try:
        store = Store(args.database)
    except Exception as exc:
        _error(f"Cannot open database: {args.database}",
               hint="Check that the database file exists. Run 'analyze' first to create it.",
               details=str(exc))
    count = store.export_csv(str(csv_path))
    if count == 0:
        print(panel("Export complete",
                    f"  {dim('No observations to export.')}"))
    else:
        print(panel("Export complete",
                    f"  {bold(str(count))} observation{'s' if count != 1 else ''} → {cyan(csv_path)}"))


def _sig(value, fmt="{:+.3f}"):
    return "  n/a" if value is None else fmt.format(value)


def _flag_color(txt):
    if "deteriorating" in txt:
        return accent_err(txt)
    return accent_warn(txt) if txt != "stable" else green(txt)


def trend(args):
    db_path = Path(args.database)
    if not db_path.exists():
        _error(f"Database not found: {db_path}",
               hint="Run 'analyze' or 'capture' first to create the database.")
    store = Store(args.database)
    config = load_runtime_config(args.config)
    source_prefix = None
    if getattr(args, "source", None):
        source_prefix = "video" if args.source == "video" else "image"
    if source_prefix and args.tree:
        obs = store.recent_by_source(source_prefix, tree_id=args.tree, limit=args.limit or 1_000_000)
    elif source_prefix:
        obs = store.recent_by_source(source_prefix, limit=args.limit or 1_000_000)
    elif args.tree:
        obs = store.recent_by_tree(args.tree, args.limit or 1_000_000)
    else:
        obs = store.recent(args.limit or 1_000_000)
    analysis = analyze_health_trend(obs, cfg=config)
    if not analysis.get("ok"):
        _error(f"Trend analysis failed: {analysis.get('error', 'unknown error')}",
               hint="Need at least 1 observation with a valid timestamp. "
                    "Run 'analyze' or 'capture' first to collect data.")
    p, c = analysis["period"], analysis["count"]
    # Filter badge
    filter_parts = []
    if getattr(args, "source", None):
        filter_parts.append(f"source={cyan(args.source)}")
    if getattr(args, "tree", None):
        filter_parts.append(f"tree={cyan(args.tree)}")
    filter_str = f"  {dim('|')}  ".join(filter_parts) if filter_parts else None
    header = (f"  {bold('Period')}    {cyan(p['start'][:10])} → {cyan(p['end'][:10])}  "
              f"({bold(str(p['days']))} days)\n"
              f"  {bold('Dataset')}   {bold(str(c['total']))} observations → "
              f"{bold(str(c['unique']))} unique  "
              f"({c['redundant_dropped']} dupes, {c['bad_dropped']} low-quality skipped)")
    if filter_str:
        header += f"\n  {bold('Filter')}    {filter_str}"
    print(panel("Health trend", header))

    print(bold("Timeline (unique captures):"))
    print(f"  {dim('Date'):16}  {dim('Src'):>5}  {dim('L'):>3}  {dim('F'):>3}  "
          f"{dim('Green'):>6}  {dim('Ripeness'):>8}  {dim('Wrinkle'):>8}")
    for r in analysis["series"]:
        date_part = r["observed_at"][:16].replace("T", " ")
        rip = f"{r['avg_ripeness']:.2f}" if r["avg_ripeness"] is not None else "  —"
        wrk = f"{r['avg_wrinkle']:.2f}" if r["avg_wrinkle"] is not None else "  —"
        src = r['source']
        leaves_s = str(r['leaves']).rjust(3)
        fruits_s = str(r['fruits']).rjust(3)
        green_s = f"{r['green']:>5.1f}%"
        if src.startswith("video"):
            src_badge = yellow("VID")
        elif src.startswith("camera"):
            src_badge = cyan("CAM")
        else:
            src_badge = green("IMG")
        print(f"  {dim(date_part)}  {src_badge}  {cyan(leaves_s)}  "
              f"{green(fruits_s)}  {yellow(green_s)}  "
              f"{rip:>8}  {wrk:>8}")

    t = analysis["trends"]
    def _trend_arrow(val, fmt="{:+.3f}", unit=""):
        if val is None:
            return dim("  n/a")
        s = fmt.format(val)
        if val > 0.001:
            return accent_err(f"↑ {s}{unit}")
        elif val < -0.001:
            return accent_ok(f"↓ {s}{unit}")
        else:
            return dim(f"→ {s}{unit}")
    print(bold("Trends (change per day):"))
    print(f"  fruit count  {_trend_arrow(t['fruit_count_per_day'])}")
    print(f"  green cov.   {_trend_arrow(t['green_per_day'], '{:+.2f}', '%/day')}")
    print(f"  ripeness     {_trend_arrow(t['ripeness_per_day'], unit='/day')}")
    print(f"  wrinkle      {_trend_arrow(t['wrinkle_per_day'], unit='/day')}")

    tracks = analysis["fruit_tracks"]
    print(bold(f"Tracked fruits (seen on 2+ distinct days): {len(tracks)}"))
    if not tracks:
        print("  (none yet — keep monitoring so colour/wrinkle changes can be followed)")
    else:
        print(f"  {dim('#'):>2}  {dim('Pos'):>10}  {dim('Obs'):>3}  {dim('Period'):>23}  "
              f"{dim('Ripeness'):>12}  {dim('Wrinkle'):>12}  {dim('Status')}")
        for tr in tracks:
            flag_txt = ", ".join(tr["flags"]) if tr["flags"] else "stable"
            when = f"{tr['first'][:10]} → {tr['last'][:10]}"
            rip = (f"{tr['ripeness_first']:.2f}→{tr['ripeness_last']:.2f}"
                   if tr['ripeness_first'] is not None else "  —  ")
            wrk = (f"{tr['wrinkle_first']:.2f}→{tr['wrinkle_last']:.2f}"
                   if tr['wrinkle_first'] is not None else "  —  ")
            fid = f"#{tr['id']}"
            pos = f"({tr['x']},{tr['y']})"
            print(f"  {cyan(fid):>3}  {pos:>10}  {tr['observations']:>3}  "
                  f"{dim(when):>23}  {rip:>12}  {wrk:>12}  {_flag_color(flag_txt)}")

    health = analysis["health"]
    level, color = {
        "stable": ("STABLE", accent_ok),
        "maturing": ("MATURING", accent_ok),
        "declining": ("DECLINING", accent_err),
        "mixed": ("MIXED", accent_warn),
        "insufficient": ("INSUFFICIENT DATA", accent_warn),
    }[health["level"]]
    desc = {
        "stable": "no significant health change",
        "maturing": "fruits are ripening",
        "declining": "wrinkling / dehydration trend",
        "mixed": "some changes improving, some worsening",
        "insufficient": "keep monitoring for 2+ days",
    }[health["level"]]
    body = [f"  {color(f'[{level}]')}  {dim(desc)}"]
    body += [f"  {dim('•')} {note}" for note in health["notes"]]
    print(panel("Health verdict", "\n".join(body)))

def _trend_text(analysis) -> str:
    """Plain-text rendering of a health-trend analysis (for the GUI)."""
    if not analysis.get("ok"):
        return analysis.get("error", "no trend data")
    p, c = analysis["period"], analysis["count"]
    lines = [f"Period   : {p['start']} -> {p['end']}  ({p['days']} distinct days)",
             f"Dataset  : {c['total']} observations -> {c['unique']} unique captures "
             f"({c['redundant_dropped']} duplicates, {c['bad_dropped']} low-quality skipped)",
             "", "Timeline:"]
    for r in analysis["series"]:
        date_part = r["observed_at"][:16].replace("T", " ")
        rip = f"{r['avg_ripeness']:.2f}" if r["avg_ripeness"] is not None else "n/a"
        wrk = f"{r['avg_wrinkle']:.2f}" if r["avg_wrinkle"] is not None else "n/a"
        lines.append(f"  {date_part}  leaves={r['leaves']:<3} fruits={r['fruits']:<3} "
                     f"green={r['green']:>5.1f}%  ripeness={rip}  wrinkle={wrk}")

    def sig(value, fmt="{:+.3f}"):
        return "n/a" if value is None else fmt.format(value)

    t = analysis["trends"]
    lines += ["", "Trends (change per day):",
              f"  fruit count : {sig(t['fruit_count_per_day'])}",
              f"  leaf count  : {sig(t.get('leaf_count_per_day'), '{:+.1f}')} /day",
              f"  green cov.  : {sig(t['green_per_day'], '{:+.2f}')} %/day",
              f"  ripeness    : {sig(t['ripeness_per_day'])}/day",
              f"  wrinkle     : {sig(t['wrinkle_per_day'])}/day"]

    tracks = analysis["fruit_tracks"]
    lines += ["", f"Tracked fruits (2+ distinct days): {len(tracks)}"]
    if not tracks:
        lines.append("  (none yet - keep monitoring so colour/wrinkle changes can be followed)")
    for tr in tracks:
        flag_txt = ", ".join(tr["flags"]) if tr["flags"] else "stable"
        when = f"{tr['first'][:10]} -> {tr['last'][:10]}"
        rip = (f"{tr['ripeness_first']:.2f}->{tr['ripeness_last']:.2f}"
               if tr['ripeness_first'] is not None else "n/a")
        wrk = (f"{tr['wrinkle_first']:.2f}->{tr['wrinkle_last']:.2f}"
               if tr['wrinkle_first'] is not None else "n/a")
        shrink = (f"{tr['shrink_ratio']:.2f}" if tr.get('shrink_ratio') is not None else "n/a")
        dehy = (f"{tr['dehydration']:.2f}" if tr.get('dehydration') else "0.00")
        area_info = ""
        if tr.get("area_first") is not None and tr.get("area_last") is not None:
            area_info = f"  area {tr['area_first']}->{tr['area_last']}"
        lines.append(f"  #{tr['id']:>2}  pos=({tr['x']},{tr['y']})  obs={tr['observations']:>2}  {when}  "
                     f"ripeness {rip}  wrinkle {wrk}  shrink {shrink}  dehy={dehy}{area_info}  [{flag_txt}]")

    health = analysis["health"]
    labels = {
        "stable": "STABLE - no significant health change",
        "maturing": "MATURING - fruits are ripening",
        "declining": "DECLINING - wrinkling / dehydration trend",
        "mixed": "MIXED - some changes improving, some worsening",
        "insufficient": "INSUFFICIENT DATA - keep monitoring for 2+ days",
    }
    lines += ["", "HEALTH: " + labels.get(health["level"], health["level"])]
    lines += [f"  - {note}" for note in health["notes"]]
    return "\n".join(lines)

def analyze_video_cli(args):
    logger = build_logger(args.verbose)
    analyzer, store, config = resources(args)
    path = Path(args.video)
    if not path.exists():
        _error(f"Video not found: {path}",
               hint=f"Check the path. Current directory: {Path.cwd()}")
    if not path.is_file():
        _error(f"Path is not a file: {path}",
               hint="Provide a path to a video file, not a directory")
    logger.info("Analysing video: %s", path)
    va = VideoAnalyzer(analyzer, config, store=store)
    out_dir = str(Path(args.output) / "video")
    bar = ProgressBar(100, label="Video")
    cap = cv2.VideoCapture(str(path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if cap.isOpened() else 0
    cap.release()
    def on_progress(done, total, _result):
        bar.update(done, note="tracked frames")
    summary = va.analyze_video(str(path), out_dir, frame_interval=args.interval,
                               progress_callback=on_progress, persist=True)
    bar.finish()
    analyzed = summary.get("analyzed_frames", 0)
    dur = summary.get("duration_sec", 0)
    tree_ids = summary.get("tree_ids", [])
    per_tree = summary.get("per_tree", {})
    lines = [
        f"  {bold('Frames')}    {analyzed} analysed / {total_frames} total  "
        f"({dur}s, {summary.get('video_fps', 0)} fps)",
        f"  {bold('Leaf')}      avg {summary.get('leaf_count_avg', 0)}  "
        f"(min {summary.get('leaf_count_min', 0)} / max {summary.get('leaf_count_max', 0)})  "
        f"curl {summary.get('leaf_curl_avg', 0):.3f}  curled {summary.get('curled_leaf_pct_avg', 0):.1f}%  "
        f"roughness {summary.get('leaf_roughness_avg', 0):.3f}",
        f"  {bold('Fruit')}      avg {summary.get('fruit_count_avg', 0)}  "
        f"(min {summary.get('fruit_count_min', 0)} / max {summary.get('fruit_count_max', 0)})  "
        f"wrinkled {summary.get('wrinkled_fruit_avg', 0)}",
        f"  {bold('Green')}      avg {yellow(str(round(summary.get('green_coverage_avg', 0), 1)) + '%')}  "
        f"fruit cover {summary.get('fruit_cover_avg', 0):.1f}%",
        f"  {bold('Colour')}     leaf hue {summary.get('leaf_avg_hue_avg', 0)}  "
        f"fruit hue {summary.get('fruit_avg_hue_avg', 0)}",
        f"  {bold('Blur')}       level {summary.get('blur_level_avg', 0):.3f}",
    ]
    mt = summary.get("fruit_maturity_total", {})
    if mt:
        mt_str = "  ".join(f"{k}={v}" for k, v in sorted(mt.items()))
        lines.append(f"  {bold('Maturity')}   {mt_str}")
    wt = summary.get("fruit_wrinkle_total", {})
    if wt:
        wt_str = "  ".join(f"{k}={v}" for k, v in sorted(wt.items()))
        lines.append(f"  {bold('Wrinkle')}    {wt_str}")
    if tree_ids:
        lines.append(f"  {bold('Trees')}      {', '.join(cyan(t) for t in tree_ids)}")
        for tid, info in sorted(per_tree.items()):
            lines.append(f"    {cyan(tid):>14}  frames={info['frames']:>3}  "
                         f"leaf={info['leaf_count_avg']}  fruit={info['fruit_count_avg']}  "
                         f"green={info['green_coverage_avg']}%  curl={info['leaf_curl_avg']:.3f}")
    lines.append(f"  {bold('Tracking')}   leaves max {summary.get('tracked_leaves_max', 0)}  "
                 f"fruits max {summary.get('tracked_fruits_max', 0)}")
    print(panel(f"Video summary: {path.name}", "\n".join(lines)))
    logger.info("Video analysis complete: %d frames analysed", analyzed)


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
def gui(args):
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog
    except ImportError:
        raise SystemExit("GUI needs Tk. On Raspberry Pi OS: sudo apt install python3-tk")

    analyzer, store, config = resources(args)
    cancel_event = threading.Event()

    # ------------------------------------------------------------------ root
    root = tk.Tk()
    root.title("OliveVision AI")
    # Fit the window to the actual screen so it never overflows the desktop.
    root.update_idletasks()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    win_w = max(780, min(1100, sw - 60))
    win_h = max(560, min(740, sh - 120))
    root.geometry(f"{win_w}x{win_h}+{max(0, (sw - win_w) // 2)}+{max(0, (sh - win_h) // 3)}")
    root.minsize(min(900, win_w), min(620, win_h))

    # Dark colour palette
    BG = "#1e1e2e"
    SURFACE = "#282840"
    CARD = "#2e2e48"
    BORDER = "#3a3a56"
    TEXT = "#cdd6f4"
    TEXT_DIM = "#7f849c"
    ACCENT = "#a6e3a1"
    ACCENT2 = "#fab387"
    BTN_BG = "#313244"
    BTN_HOVER = "#45475a"
    SLIDER_TR = "#45475a"
    root.configure(bg=BG)

    # ------------------------------------------------------------------ style
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=BG, foreground=TEXT, font=("Segoe UI", 9))
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)
    style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 9))
    style.configure("Dim.TLabel", background=BG, foreground=TEXT_DIM, font=("Segoe UI", 8))
    style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground=ACCENT, background=BG)
    style.configure("Big.TLabel", font=("Segoe UI", 22, "bold"), foreground=ACCENT, background=BG)
    style.configure("Card.TLabel", background=CARD, foreground=TEXT, font=("Segoe UI", 9))
    style.configure("CardHeader.TLabel", background=CARD, foreground=ACCENT, font=("Segoe UI", 10, "bold"))
    style.configure("CardDim.TLabel", background=CARD, foreground=TEXT_DIM, font=("Segoe UI", 8))

    # Buttons
    style.configure("TButton", background=BTN_BG, foreground=TEXT, borderwidth=0,
                    font=("Segoe UI", 9), padding=[12, 6])
    style.map("TButton",
              background=[("active", BTN_HOVER), ("pressed", "#585b70")],
              foreground=[("active", TEXT)])
    style.configure("Accent.TButton", background=ACCENT, foreground="#1e1e2e",
                    font=("Segoe UI", 9, "bold"), borderwidth=0, padding=[14, 7])
    style.map("Accent.TButton",
              background=[("active", "#94e29b"), ("pressed", "#88d690")])
    style.configure("Danger.TButton", background="#f38ba8", foreground="#1e1e2e",
                    font=("Segoe UI", 9, "bold"), borderwidth=0, padding=[10, 6])
    style.map("Danger.TButton",
              background=[("active", "#eba0ac"), ("pressed", "#e08090")])

    # Notebook
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", background=BG, foreground=TEXT_DIM,
                    font=("Segoe UI", 9), padding=[14, 6])
    style.map("TNotebook.Tab",
              background=[("selected", CARD)],
              foreground=[("selected", ACCENT)])

    # Progress bar
    style.configure("Horizontal.TProgressbar", troughcolor=SLIDER_TR, background=ACCENT,
                    borderwidth=0, lightcolor=ACCENT, darkcolor=ACCENT)

    # Slider
    style.configure("Horizontal.TScale", background=BG, troughcolor=SLIDER_TR,
                    borderwidth=0, sliderthickness=14)

    # LabelFrame (cards)
    style.configure("Card.TLabelframe", background=CARD, foreground=ACCENT,
                    bordercolor=BORDER, borderwidth=1, relief="solid")
    style.configure("Card.TLabelframe.Label", background=CARD, foreground=ACCENT,
                    font=("Segoe UI", 10, "bold"))

    # Treeview
    style.configure("Treeview", background=SURFACE, foreground=TEXT,
                    fieldbackground=SURFACE, borderwidth=0, font=("Segoe UI", 8), rowheight=24)
    style.configure("Treeview.Heading", background=BG, foreground=TEXT_DIM,
                    font=("Segoe UI", 8, "bold"), borderwidth=0)
    style.map("Treeview", background=[("selected", "#45475a")], foreground=[("selected", ACCENT)])

    # ================================================================ layout
    # Top toolbar
    toolbar = ttk.Frame(root)
    toolbar.pack(fill="x", padx=12, pady=(10, 0))

    ttk.Label(toolbar, text="OliveVision", style="Big.TLabel").pack(side="left", padx=(0, 16))

    btn_open = ttk.Button(toolbar, text="  Open Image  ", command=lambda: None)
    btn_open.pack(side="left", padx=3)
    btn_cam = ttk.Button(toolbar, text="  Capture  ", command=lambda: None)
    btn_cam.pack(side="left", padx=3)
    btn_video = ttk.Button(toolbar, text="  Open Video  ", command=lambda: None)
    btn_video.pack(side="left", padx=3)
    btn_recent = ttk.Button(toolbar, text="  History  ", command=lambda: None)
    btn_recent.pack(side="left", padx=3)
    btn_trend = ttk.Button(toolbar, text="  Trend  ", command=lambda: None)
    btn_trend.pack(side="left", padx=3)

    ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=12)
    lbl_status = tk.StringVar(value="Ready")
    ttk.Label(toolbar, textvariable=lbl_status, style="Dim.TLabel").pack(side="left")
    lbl_mode = ttk.Label(toolbar, text="", style="Dim.TLabel")
    lbl_mode.pack(side="left", padx=12)

    # Progress bar + cancel + settings
    progress = ttk.Progressbar(toolbar, mode="indeterminate", length=150)
    progress.pack(side="right", padx=(8, 0))
    btn_cancel = ttk.Button(toolbar, text="  Cancel  ", command=lambda: cancel_event.set(),
                            state="disabled", style="Danger.TButton")
    btn_cancel.pack(side="right", padx=4)
    btn_settings = ttk.Button(toolbar, text="  Settings  ", command=lambda: None)
    btn_settings.pack(side="right", padx=4)

    # Main area: left (preview + tabs) | right (params + results)
    main = ttk.Frame(root)
    main.pack(fill="both", expand=True, padx=12, pady=10)
    main.columnconfigure(0, weight=3)
    main.columnconfigure(1, weight=2)
    main.rowconfigure(0, weight=1)

    left = ttk.Frame(main)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    left.rowconfigure(1, weight=1)
    left.columnconfigure(0, weight=1)

    right = ttk.Frame(main)
    right.grid(row=0, column=1, sticky="nsew")
    right.rowconfigure(2, weight=1)
    right.columnconfigure(0, weight=1)

    # ---- LEFT: preview image
    preview_frame = tk.Frame(left, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
    preview_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
    preview_label = tk.Label(preview_frame, text="No image loaded", bg=CARD, fg=TEXT_DIM,
                             anchor="center", font=("Segoe UI", 10))
    preview_label.pack(fill="both", expand=True, padx=6, pady=6)

    # ---- LEFT: notebook with Log / History / Hue Histogram / Timeline
    notebook = ttk.Notebook(left)
    notebook.grid(row=1, column=0, sticky="nsew")

    # --- Log tab
    log_frame = tk.Frame(notebook, bg=SURFACE)
    notebook.add(log_frame, text="  Log  ")
    log_text = tk.Text(log_frame, height=8, state="disabled", font=("Cascadia Code", 9),
                       bg=SURFACE, fg=TEXT, insertbackground=TEXT, wrap="word",
                       borderwidth=0, highlightthickness=0)
    log_scroll = ttk.Scrollbar(log_frame, command=log_text.yview)
    log_text.configure(yscrollcommand=log_scroll.set)
    log_scroll.pack(side="right", fill="y")
    log_text.pack(fill="both", expand=True)

    # --- History tab
    hist_frame = tk.Frame(notebook, bg=SURFACE)
    notebook.add(hist_frame, text="  History  ")
    cols = ("time", "source", "tree", "leaves", "fruits", "green%", "leaf_color", "fruit_mat")
    history_tree = ttk.Treeview(hist_frame, columns=cols, show="headings", height=8)
    col_widths = {"time": 130, "source": 70, "tree": 80, "leaves": 55, "fruits": 55, "green%": 60, "leaf_color": 90, "fruit_mat": 80}
    for c in cols:
        history_tree.heading(c, text=c)
        history_tree.column(c, width=col_widths.get(c, 80), anchor="center")
    h_scroll = ttk.Scrollbar(hist_frame, command=history_tree.yview)
    history_tree.configure(yscrollcommand=h_scroll.set)
    h_scroll.pack(side="right", fill="y")
    history_tree.pack(fill="both", expand=True)

    # --- Trend tab (health trend report from the database)
    trend_frame = tk.Frame(notebook, bg=SURFACE)
    notebook.add(trend_frame, text="  Trend  ")
    trend_text = tk.Text(trend_frame, state="disabled", wrap="word",
                         font=("Cascadia Code", 9), bg=SURFACE, fg=TEXT,
                         insertbackground=TEXT, borderwidth=0, highlightthickness=0)
    trend_scroll = ttk.Scrollbar(trend_frame, command=trend_text.yview)
    trend_text.configure(yscrollcommand=trend_scroll.set)
    trend_scroll.pack(side="right", fill="y")
    trend_text.pack(fill="both", expand=True)

    # --- Hue Histogram tab (Canvas)
    hue_frame = tk.Frame(notebook, bg=SURFACE)
    notebook.add(hue_frame, text="  Hue Histogram  ")
    hue_canvas = tk.Canvas(hue_frame, bg=SURFACE, highlightthickness=0)
    hue_canvas.pack(fill="both", expand=True)

    # --- Video Timeline tab (Canvas)
    timeline_frame = tk.Frame(notebook, bg=SURFACE)
    notebook.add(timeline_frame, text="  Timeline  ")
    timeline_canvas = tk.Canvas(timeline_frame, bg=SURFACE, highlightthickness=0)
    timeline_canvas.pack(fill="both", expand=True)

    # --- Detection Explanation tab (Text)
    explain_frame = tk.Frame(notebook, bg=SURFACE)
    notebook.add(explain_frame, text="  Why? (Explanation)  ")
    explain_text = tk.Text(explain_frame, state="disabled", wrap="word",
                           font=("Cascadia Code", 9), bg=SURFACE, fg=TEXT,
                           insertbackground=TEXT, borderwidth=0, highlightthickness=0)
    explain_scroll = ttk.Scrollbar(explain_frame, command=explain_text.yview)
    explain_text.configure(yscrollcommand=explain_scroll.set)
    explain_scroll.pack(side="right", fill="y")
    explain_text.pack(fill="both", expand=True)

    # --- Pipeline Diagnostics tab (Text, plain monospace table)
    diag_frame = tk.Frame(notebook, bg=SURFACE)
    notebook.add(diag_frame, text="  Diagnostics  ")
    diag_text = tk.Text(diag_frame, state="disabled", wrap="none",
                        font=("Cascadia Code", 9), bg=SURFACE, fg=TEXT,
                        insertbackground=TEXT, borderwidth=0, highlightthickness=0)
    diag_scroll = ttk.Scrollbar(diag_frame, command=diag_text.yview)
    diag_text.configure(yscrollcommand=diag_scroll.set)
    diag_scroll.pack(side="right", fill="y")
    diag_text.pack(fill="both", expand=True)

    # --- Soil Moisture tab (Text + toggle)
    soil_frame = tk.Frame(notebook, bg=SURFACE)
    notebook.add(soil_frame, text="  Soil Moisture  ")
    soil_text = tk.Text(soil_frame, state="disabled", wrap="word",
                        font=("Cascadia Code", 9), bg=SURFACE, fg=TEXT,
                        insertbackground=TEXT, borderwidth=0, highlightthickness=0)
    soil_scroll = ttk.Scrollbar(soil_frame, command=soil_text.yview)
    soil_text.configure(yscrollcommand=soil_scroll.set)
    soil_scroll.pack(side="right", fill="y")
    soil_text.pack(fill="both", expand=True)

    # Soil moisture on/off toggle (in toolbar)
    soil_enabled = tk.BooleanVar(value=True)
    btn_soil = ttk.Checkbutton(toolbar, text="  Soil Moisture  ", variable=soil_enabled,
                                style="TCheckbutton")
    btn_soil.pack(side="left", padx=3)

    # AI Upscale on/off toggle (in toolbar) + threshold/model picker
    upscale_enabled = tk.BooleanVar(value=bool(getattr(args, "upscale", False)))
    btn_up = ttk.Checkbutton(toolbar, text="  AI Upscale  ", variable=upscale_enabled,
                              style="TCheckbutton")
    btn_up.pack(side="left", padx=3)

    # ---- RIGHT: Parameter panel (card)
    param_frame = ttk.LabelFrame(right, text=" Detection Parameters ", style="Card.TLabelframe")
    param_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 6))

    sliders = {}
    slider_defs = [
        ("leaf_hue_lo",    "Leaf Hue Min",    0,   179, config["detection"]["leaf_hue"][0]),
        ("leaf_hue_hi",    "Leaf Hue Max",    0,   179, config["detection"]["leaf_hue"][1]),
        ("leaf_sat_min",   "Leaf Sat Min",    0,   255, config["detection"]["leaf_saturation_min"]),
        ("leaf_val_min",   "Leaf Val Min",    0,   255, config["detection"]["leaf_value_min"]),
        ("leaf_min_area",  "Leaf Min Area",   50,  5000, config["detection"]["leaf_min_area"]),
        ("fruit_hue_lo",   "Fruit Hue Min",   0,   179, config["detection"]["fruit_hue_yellow"][0]),
        ("fruit_hue_hi",   "Fruit Hue Max",   0,   179, config["detection"]["fruit_hue_yellow"][1]),
        ("fruit_sat_min",  "Fruit Sat Min",   0,   255, config["detection"]["fruit_saturation_min"]),
        ("fruit_min_area", "Fruit Min Area",  20,  3000, config["detection"]["fruit_min_area"]),
    ]

    for i, (key, label, lo, hi, default) in enumerate(slider_defs):
        ttk.Label(param_frame, text=label, style="CardDim.TLabel").grid(
            row=i, column=0, sticky="w", padx=8, pady=2)
        var = tk.IntVar(value=default)
        s = ttk.Scale(param_frame, from_=lo, to=hi, variable=var, orient="horizontal")
        s.grid(row=i, column=1, sticky="ew", padx=4, pady=2)
        val_lbl = tk.Label(param_frame, textvariable=var, width=5, bg=CARD, fg=ACCENT,
                           font=("Cascadia Code", 9))
        val_lbl.grid(row=i, column=2, padx=8)
        sliders[key] = var
    param_frame.columnconfigure(1, weight=1)

    # Detection mode selector
    mode_row = len(slider_defs)
    ttk.Label(param_frame, text="Detect Mode", style="CardDim.TLabel").grid(
        row=mode_row, column=0, sticky="w", padx=8, pady=(8, 2))
    mode_var = tk.StringVar(value=config["detection"].get("detect_mode", "multi_signal"))
    mode_options = ["multi_signal", "kmeans", "grabcut", "bg_removal", "edge_flood", "adaptive"]
    mode_combo = ttk.Combobox(param_frame, textvariable=mode_var, values=mode_options,
                               state="readonly", width=16, font=("Segoe UI", 9))
    mode_combo.grid(row=mode_row, column=1, columnspan=2, sticky="w", padx=4, pady=(8, 2))

    # Mask view checkboxes
    mask_row = mode_row + 1
    ttk.Label(param_frame, text="Show Masks", style="CardDim.TLabel").grid(
        row=mask_row, column=0, sticky="w", padx=8, pady=(4, 2))
    show_leaf_mask = tk.BooleanVar(value=False)
    show_fruit_mask = tk.BooleanVar(value=False)
    show_fg_mask = tk.BooleanVar(value=False)
    cb_frame = tk.Frame(param_frame, bg=CARD)
    cb_frame.grid(row=mask_row, column=1, columnspan=2, sticky="w", padx=4, pady=(4, 2))
    tk.Checkbutton(cb_frame, text="Leaf", variable=show_leaf_mask, bg=CARD, fg="#a6e3a1",
                   selectcolor=BORDER, activebackground=CARD, activeforeground="#a6e3a1",
                   font=("Segoe UI", 8)).pack(side="left", padx=2)
    tk.Checkbutton(cb_frame, text="Fruit", variable=show_fruit_mask, bg=CARD, fg="#fab387",
                   selectcolor=BORDER, activebackground=CARD, activeforeground="#fab387",
                   font=("Segoe UI", 8)).pack(side="left", padx=2)
    tk.Checkbutton(cb_frame, text="FG", variable=show_fg_mask, bg=CARD, fg="#89b4fa",
                   selectcolor=BORDER, activebackground=CARD, activeforeground="#89b4fa",
                   font=("Segoe UI", 8)).pack(side="left", padx=2)

    qr_row = mask_row + 1
    ttk.Label(param_frame, text="QR Detection", style="CardDim.TLabel").grid(
        row=qr_row, column=0, sticky="w", padx=8, pady=(4, 2))
    qr_detection_var = tk.BooleanVar(value=config["detection"].get("qr_detection", True))
    tk.Checkbutton(param_frame, text="Enabled", variable=qr_detection_var, bg=CARD, fg="#f9e2af",
                   selectcolor=BORDER, activebackground=CARD, activeforeground="#f9e2af",
                   font=("Segoe UI", 8)).grid(row=qr_row, column=1, sticky="w", padx=4, pady=(4, 2))

    btn_reset = ttk.Button(param_frame, text="Reset Defaults", command=lambda: None)
    btn_reset.grid(row=mask_row + 1, column=0, columnspan=3, pady=8)

    # ---- RIGHT: Stat cards (big numbers)
    stat_frame = tk.Frame(right, bg=BG)
    stat_frame.grid(row=1, column=0, sticky="ew", pady=(0, 6))
    for c in range(3):
        stat_frame.columnconfigure(c, weight=1)

    def _make_stat_card(parent, title, color):
        card = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        tk.Label(card, text=title, bg=CARD, fg=TEXT_DIM, font=("Segoe UI", 7),
                 anchor="w").pack(fill="x", padx=8, pady=(6, 0))
        var = tk.StringVar(value="--")
        tk.Label(card, textvariable=var, bg=CARD, fg=color,
                 font=("Segoe UI", 20, "bold")).pack(fill="x", padx=8, pady=(0, 6))
        return var

    stat_leaf = _make_stat_card(stat_frame, "LEAVES", ACCENT)
    stat_fruit = _make_stat_card(stat_frame, "FRUITS", ACCENT2)
    stat_green = _make_stat_card(stat_frame, "GREEN %", "#89b4fa")
    for i, card in enumerate(stat_frame.winfo_children()):
        card.grid(row=0, column=i, sticky="ew", padx=2)

    # ---- RIGHT: Results panel (card)
    result_frame = ttk.LabelFrame(right, text=" Analysis Results ", style="Card.TLabelframe")
    result_frame.grid(row=2, column=0, sticky="nsew", pady=(4, 0))
    result_frame.columnconfigure(0, weight=1)
    result_frame.rowconfigure(0, weight=1)

    # Scrollable content: rows live on an inner canvas so many fields can be seen.
    result_canvas = tk.Canvas(result_frame, bg=CARD, highlightthickness=0)
    result_scroll = ttk.Scrollbar(result_frame, orient="vertical", command=result_canvas.yview)
    result_canvas.configure(yscrollcommand=result_scroll.set)
    result_canvas.grid(row=0, column=0, sticky="nsew")
    result_scroll.grid(row=0, column=1, sticky="ns")
    result_inner = ttk.Frame(result_canvas, style="Card.TFrame")
    result_window = result_canvas.create_window((0, 0), window=result_inner, anchor="nw")

    def _config_result_scroll(_event=None):
        result_canvas.configure(scrollregion=result_canvas.bbox("all"))
        result_canvas.itemconfigure(result_window, width=result_canvas.winfo_width())
    result_canvas.bind("<Configure>", _config_result_scroll)
    result_inner.bind("<Configure>", _config_result_scroll)
    result_inner.bind("<Enter>", lambda _e: result_canvas.bind_all("<MouseWheel>",
        lambda e: result_canvas.yview_scroll(-1 * (e.delta // 120), "units")))
    result_inner.bind("<Leave>", lambda _e: result_canvas.unbind_all("<MouseWheel>"))

    result_vars = {}
    result_fields = [
        ("leaf_count",      "Leaves"),
        ("fruit_count",     "Fruits"),
        ("green_coverage",  "Green Coverage %"),
        ("fruit_cover_pct", "Fruit Coverage %"),
        ("leaf_color_stage","Leaf Color"),
        ("leaf_senescence", "Senescence %"),
        ("leaf_avg_hue",    "Leaf Avg Hue"),
        ("leaf_confidence", "Leaf Confidence"),
        ("fruit_maturity",  "Fruit Maturity"),
        ("fruit_maturity_breakdown", "Fruit Breakdown"),
        ("wrinkled_fruit_count", "Wrinkled Fruits"),
        ("fruit_wrinkle_summary", "Wrinkle Breakdown"),
        ("fruit_avg_hue",   "Fruit Avg Hue"),
        ("fruit_avg_area",  "Fruit Avg Area"),
        ("fruit_confidence","Fruit Confidence"),
        ("leaf_roughness",  "Leaf Roughness"),
    ]
    result_inner.columnconfigure(1, weight=1)
    for i, (key, label) in enumerate(result_fields):
        ttk.Label(result_inner, text=label, style="CardDim.TLabel").grid(
            row=i, column=0, sticky="w", padx=8, pady=2)
        v = tk.StringVar(value="--")
        lbl = tk.Label(result_inner, textvariable=v, bg=CARD, fg=TEXT,
                       font=("Segoe UI", 9, "bold"), anchor="w")
        lbl.grid(row=i, column=1, sticky="w", padx=8, pady=2)
        result_vars[key] = v

    # ========================================================== internal state
    current_image_bgr = None
    current_result = None
    history_log = deque(maxlen=200)

    # App mode: "experiment" (continuous observation, saved to DB) or
    # "single" (one-shot image/video detection, nothing written to the DB).
    settings_path = Path(args.database).parent / "gui_settings.json"
    mode_var = tk.StringVar(value="experiment")
    try:
        if settings_path.exists():
            saved = json.loads(settings_path.read_text(encoding="utf-8"))
            if saved.get("mode") in ("experiment", "single"):
                mode_var.set(saved["mode"])
    except Exception:
        pass

    # ========================================================== helpers
    def write_log(msg):
        def _do():
            log_text.configure(state="normal")
            log_text.insert("end", msg + "\n")
            log_text.see("end")
            log_text.configure(state="disabled")
        root.after(0, _do)

    def set_status(msg):
        root.after(0, lambda: lbl_status.set(msg))

    def run_in_background(work_fn):
        def runner():
            root.after(0, lambda: (progress.start(12), btn_cancel.configure(state="normal")))
            cancel_event.clear()
            try:
                work_fn()
            except Exception as exc:
                write_log(f"ERROR [{type(exc).__name__}]: {exc}")
            finally:
                root.after(0, lambda: (progress.stop(), btn_cancel.configure(state="disabled")))
        threading.Thread(target=runner, daemon=True).start()

    def show_preview_cv(image_bgr, max_w=500, max_h=340):
        h, w = image_bgr.shape[:2]
        scale = min(max_w / w, max_h / h, 1.0)
        resized = cv2.resize(image_bgr, (int(w * scale), int(h * scale)))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        ok, encoded = cv2.imencode(".ppm", rgb)
        if ok:
            photo = tk.PhotoImage(data=encoded.tobytes(), format="PPM")
            preview_label.configure(image=photo, text="")
            preview_label.image = photo

    def update_results(r):
        for key, var in result_vars.items():
            val = r.get(key, "--")
            if isinstance(val, dict):
                val = ", ".join(f"{k}: {v}" for k, v in val.items()) or "--"
            elif isinstance(val, float):
                val = f"{val:.2f}"
            var.set(str(val))
        stat_leaf.set(str(r.get("leaf_count", "--")))
        stat_fruit.set(str(r.get("fruit_count", "--")))
        gc = r.get("green_coverage", "--")
        stat_green.set(f"{gc:.1f}" if isinstance(gc, (int, float)) else str(gc))
        try:
            text = explain_detection(r)
            explain_text.configure(state="normal")
            explain_text.delete("1.0", "end")
            explain_text.insert("1.0", text)
            explain_text.configure(state="disabled")
        except Exception:
            pass
        try:
            diag_text.configure(state="normal")
            diag_text.delete("1.0", "end")
            diag_text.insert("1.0", _cli_diagnostics_text(r))
            diag_text.configure(state="disabled")
        except Exception:
            pass
        try:
            _update_soil_tab(r)
        except Exception:
            pass

    def _update_soil_tab(r):
        """Update the Soil Moisture tab with analysis result data."""
        soil_text.configure(state="normal")
        soil_text.delete("1.0", "end")
        sm = r.get("soil_moisture", {})
        ha = r.get("health_assessment", {})
        lines = []
        lines.append("SOIL MOISTURE INTEGRATION")
        lines.append("=" * 50)
        if not sm.get("available", False):
            lines.append("")
            lines.append("Status: Data not available")
            err = sm.get("error")
            if err:
                lines.append(f"Error: {err}")
            lines.append("")
            lines.append("Check config/soil_moisture.yaml")
            lines.append("and network connection.")
        else:
            status = sm.get("status", "unknown")
            lines.append(f"Status: {status.upper()}")
            lines.append(f"Source: {sm.get('source', '?')}")
            lines.append("")
            lines.append("--- Moisture Levels ---")
            s1 = sm.get("sensor1_percent")
            s2 = sm.get("sensor2_percent")
            avg = sm.get("average_percent")
            if s1 is not None:
                lines.append(f"  Sensor 1: {s1:.1f}%")
            if s2 is not None:
                lines.append(f"  Sensor 2: {s2:.1f}%")
            if avg is not None:
                lines.append(f"  Average:  {avg:.1f}%")
            lines.append("")
            lines.append("--- Environment ---")
            temp = sm.get("temperature")
            hum = sm.get("humidity")
            if temp is not None:
                lines.append(f"  Temperature: {temp:.1f} C")
            if hum is not None:
                lines.append(f"  Humidity:    {hum:.1f}%")
            lines.append("")
            lines.append("--- Health Assessment ---")
            risk = ha.get("moisture_risk", "unknown")
            msg = ha.get("moisture_message", "")
            lines.append(f"  Risk:    {risk.upper()}")
            lines.append(f"  Message: {msg}")
            vs = ha.get("visual_health_score", 0.5)
            ms = ha.get("moisture_health_score", 0.5)
            cs = ha.get("combined_health_score", 0.5)
            w = ha.get("moisture_weight", 0.0)
            lines.append(f"  Visual score:     {vs:.3f}")
            lines.append(f"  Moisture score:   {ms:.3f}")
            lines.append(f"  Combined score:   {cs:.3f}")
            lines.append(f"  Moisture weight:  {w:.0%}")
            flags = ha.get("flags", [])
            if flags:
                lines.append(f"  Flags: {', '.join(flags)}")
            lines.append("")
            lines.append("--- 24h Statistics ---")
            stats = sm.get("stats_24h", {})
            if stats:
                lines.append(f"  Readings: {stats.get('total_readings', '?')}")
                for key, label in [("sensor1_avg", "Sensor 1 avg"),
                                   ("sensor2_avg", "Sensor 2 avg")]:
                    v = stats.get(key)
                    if v is not None:
                        mn = stats.get(key.replace("_avg", "_min"), "?")
                        mx = stats.get(key.replace("_avg", "_max"), "?")
                        lines.append(f"  {label}: {v:.1f}%  (min {mn:.1f}, max {mx:.1f})")
            else:
                lines.append("  No statistics available")
        soil_text.insert("1.0", "\n".join(lines))
        soil_text.configure(state="disabled")

    def draw_hue_histogram(image_bgr, leaf_mask=None, fruit_mask=None):
        def _draw():
            hue_canvas.delete("all")
            cw = hue_canvas.winfo_width()
            ch = hue_canvas.winfo_height()
            if cw < 10 or ch < 10:
                return

            # Masks come from the (possibly resized) analysed image, so resize the
            # source image to match the mask shape before computing histograms.
            img_for_hist = image_bgr
            for m in (leaf_mask, fruit_mask):
                if m is not None and m.shape[:2] != img_for_hist.shape[:2]:
                    img_for_hist = cv2.resize(image_bgr, (m.shape[1], m.shape[0]))
                    break

            hsv = cv2.cvtColor(img_for_hist, cv2.COLOR_BGR2HSV)
            h_channel = hsv[:, :, 0]

            margin_l, margin_r, margin_t, margin_b = 50, 20, 25, 30
            plot_w = cw - margin_l - margin_r
            plot_h = ch - margin_t - margin_b
            if plot_w < 20 or plot_h < 20:
                return

            hist_leaf = cv2.calcHist([h_channel], [0], leaf_mask, [60], [0, 180]).flatten() if leaf_mask is not None else None
            hist_fruit = cv2.calcHist([h_channel], [0], fruit_mask, [60], [0, 180]).flatten() if fruit_mask is not None else None
            hist_all = cv2.calcHist([h_channel], [0], None, [60], [0, 180]).flatten()

            max_val = max(hist_all.max(), (hist_leaf.max() if hist_leaf is not None else 0),
                          (hist_fruit.max() if hist_fruit is not None else 0), 1)

            bin_w = plot_w / 60

            # Axes
            hue_canvas.create_line(margin_l, margin_t, margin_l, margin_t + plot_h, fill="#7f849c")
            hue_canvas.create_line(margin_l, margin_t + plot_h, margin_l + plot_w, margin_t + plot_h, fill="#7f849c")
            hue_canvas.create_text(margin_l + plot_w // 2, ch - 5, text="Hue (0-180)",
                                   font=("Segoe UI", 8), fill="#7f849c")
            for i in range(0, 61, 15):
                x = margin_l + (i / 60) * plot_w
                hue_canvas.create_line(x, margin_t + plot_h, x, margin_t + plot_h + 3, fill="#7f849c")
                hue_canvas.create_text(x, margin_t + plot_h + 6, text=str(int(180 * i / 60)),
                                       font=("Segoe UI", 7), fill="#7f849c")
            for i in range(5):
                y = margin_t + int(plot_h * (1 - i / 4))
                val = int(max_val * i / 4)
                hue_canvas.create_text(margin_l - 5, y, text=str(val), anchor="e",
                                       font=("Segoe UI", 7), fill="#7f849c")

            # All histogram (gray)
            for i in range(60):
                bar_h = int((hist_all[i] / max_val) * plot_h)
                x0 = margin_l + i * bin_w
                hue_canvas.create_rectangle(x0, margin_t + plot_h - bar_h, x0 + bin_w - 1, margin_t + plot_h,
                                            fill="#45475a", outline="")

            # Leaf histogram (green)
            if hist_leaf is not None:
                for i in range(60):
                    bar_h = int((hist_leaf[i] / max_val) * plot_h)
                    x0 = margin_l + i * bin_w
                    hue_canvas.create_rectangle(x0, margin_t + plot_h - bar_h, x0 + bin_w - 1, margin_t + plot_h,
                                                fill="#a6e3a1", outline="", stipple="gray50")

            # Fruit histogram (orange)
            if hist_fruit is not None:
                for i in range(60):
                    bar_h = int((hist_fruit[i] / max_val) * plot_h)
                    x0 = margin_l + i * bin_w
                    hue_canvas.create_rectangle(x0, margin_t + plot_h - bar_h, x0 + bin_w - 1, margin_t + plot_h,
                                                fill="#fab387", outline="", stipple="gray50")

            # Legend
            lx = margin_l + 8
            hue_canvas.create_rectangle(lx, 5, lx + 10, 15, fill="#45475a", outline="")
            hue_canvas.create_text(lx + 14, 10, text="All", anchor="w", font=("Segoe UI", 7), fill="#7f849c")
            hue_canvas.create_rectangle(lx + 45, 5, lx + 55, 15, fill="#a6e3a1", outline="")
            hue_canvas.create_text(lx + 59, 10, text="Leaf", anchor="w", font=("Segoe UI", 7), fill="#7f849c")
            hue_canvas.create_rectangle(lx + 100, 5, lx + 110, 15, fill="#fab387", outline="")
            hue_canvas.create_text(lx + 114, 10, text="Fruit", anchor="w", font=("Segoe UI", 7), fill="#7f849c")

        root.after(0, _draw)

    def draw_timeline(timeline_data):
        def _draw():
            timeline_canvas.delete("all")
            cw = timeline_canvas.winfo_width()
            ch = timeline_canvas.winfo_height()
            if cw < 20 or ch < 20 or not timeline_data:
                return
            margin_l, margin_r, margin_t, margin_b = 55, 20, 25, 45
            plot_w = cw - margin_l - margin_r
            plot_h = ch - margin_t - margin_b
            times = [t["timestamp_sec"] for t in timeline_data]
            leaves = [t["leaf_count"] for t in timeline_data]
            fruits = [t["fruit_count"] for t in timeline_data]
            greens = [t.get("green_coverage", 0.0) for t in timeline_data]
            curls = [t.get("leaf_curl_index", 0.0) for t in timeline_data]
            max_t = max(times) if times else 1
            max_count = max(max(leaves) if leaves else 1, max(fruits) if fruits else 1, 1)
            # Axes
            timeline_canvas.create_line(margin_l, margin_t, margin_l, margin_t + plot_h, fill="#7f849c")
            timeline_canvas.create_line(margin_l, margin_t + plot_h, margin_l + plot_w, margin_t + plot_h, fill="#7f849c")
            timeline_canvas.create_text(margin_l + plot_w // 2, ch - 5, text="Time (s)",
                                        font=("Segoe UI", 8), fill="#7f849c")
            for i in range(5):
                y = margin_t + int(plot_h * (1 - i / 4))
                val = int(max_count * i / 4)
                timeline_canvas.create_text(margin_l - 5, y, text=str(val), anchor="e",
                                            font=("Segoe UI", 7), fill="#7f849c")
            def plot_line(data, color, scale=1.0, offset=0):
                if len(data) < 2:
                    return
                coords = []
                for i, d in enumerate(data):
                    x = margin_l + (times[i] / max_t) * plot_w
                    y = margin_t + plot_h - ((d * scale + offset) / max_count) * plot_h
                    coords.extend([x, y])
                timeline_canvas.create_line(coords, fill=color, width=2, smooth=True)
            plot_line(leaves, "#a6e3a1")
            plot_line(fruits, "#fab387")
            # Green coverage: scale % to count range (green% max ~100 → map to max_count)
            green_scale = max_count / 100.0 if max_count > 0 else 1.0
            plot_line(greens, "#89b4fa", scale=green_scale)
            # Curl index: 0-1, scale to count range
            plot_line(curls, "#f38ba8", scale=max_count)
            # Legend (two rows)
            lx = margin_l + 8
            ly = 8
            for i, (label, color) in enumerate([
                ("Leaves", "#a6e3a1"), ("Fruits", "#fab387"),
                ("Green%", "#89b4fa"), ("Curl", "#f38ba8"),
            ]):
                col = i % 2
                row = i // 2
                x0 = lx + col * 100
                y0 = ly + row * 14
                timeline_canvas.create_line(x0, y0, x0 + 15, y0, fill=color, width=2)
                timeline_canvas.create_text(x0 + 19, y0, text=label, anchor="w",
                                            font=("Segoe UI", 7), fill="#7f849c")
        root.after(0, _draw)

    def refresh_history():
        rows = store.recent(50)
        def _do():
            history_tree.delete(*history_tree.get_children())
            for r in rows:
                t = r.get("observed_at", "")[:19]
                src = r.get("source", "")
                tid = r.get("tree_id", "")
                lc = r.get("leaf_count", "")
                fc = r.get("fruit_count", "")
                gc = r.get("green_coverage", "")
                lcolor = r.get("leaf_color_stage", "")
                fmat = r.get("fruit_maturity", "")
                history_tree.insert("", "end", values=(t, src, tid, lc, fc, gc, lcolor, fmat))
        root.after(0, _do)

    def apply_slider_config():
        d = analyzer.config["detection"]
        d["leaf_hue"] = [sliders["leaf_hue_lo"].get(), sliders["leaf_hue_hi"].get()]
        d["leaf_saturation_min"] = sliders["leaf_sat_min"].get()
        d["leaf_value_min"] = sliders["leaf_val_min"].get()
        d["leaf_min_area"] = sliders["leaf_min_area"].get()
        d["fruit_hue_yellow"] = [sliders["fruit_hue_lo"].get(), sliders["fruit_hue_hi"].get()]
        d["fruit_saturation_min"] = sliders["fruit_sat_min"].get()
        d["fruit_min_area"] = sliders["fruit_min_area"].get()
        d["detect_mode"] = mode_var.get()
        d["qr_detection"] = qr_detection_var.get()

    def reset_sliders():
        defaults = DEFAULTS_REF["detection"]
        sliders["leaf_hue_lo"].set(defaults["leaf_hue"][0])
        sliders["leaf_hue_hi"].set(defaults["leaf_hue"][1])
        sliders["leaf_sat_min"].set(defaults["leaf_saturation_min"])
        sliders["leaf_val_min"].set(defaults["leaf_value_min"])
        sliders["leaf_min_area"].set(defaults["leaf_min_area"])
        sliders["fruit_hue_lo"].set(defaults["fruit_hue_yellow"][0])
        sliders["fruit_hue_hi"].set(defaults["fruit_hue_yellow"][1])
        sliders["fruit_sat_min"].set(defaults["fruit_saturation_min"])
        sliders["fruit_min_area"].set(defaults["fruit_min_area"])
        mode_var.set(defaults.get("detect_mode", "multi_signal"))
        qr_detection_var.set(defaults.get("qr_detection", True))

    def do_analyze(image_bgr, source, path=None):
        apply_slider_config()
        # Reflect AI Upscale toggle state
        if upscale_enabled.get():
            analyzer.set_upscale(
                enabled=True,
                model=getattr(args, "upscale_model", "realesrgan-x4plus"),
                scale=getattr(args, "upscale_scale", 2),
                threshold=getattr(args, "upscale_threshold", 900))
        else:
            analyzer.set_upscale(enabled=False)
        set_status("Analysing...")
        persist = mode_var.get() == "experiment"
        result, output_path = save_observation(analyzer, store if persist else None,
                                               image_bgr, source, args.output, path,
                                               persist=persist)
        if soil_enabled.get():
            try:
                from datetime import datetime as _dt
                obs_time = _dt.fromisoformat(result.get("observed_at", ""))
                soil_data = get_moisture_for_olive_analysis(target_time=obs_time)
                result = integrate_soil_moisture(result, soil_data)
            except Exception:
                pass

        def _update():
            update_results(result)
            set_status("Complete")
            ts = result.get("observed_at", "")[:19]
            lc = result.get("leaf_count", 0)
            fc = result.get("fruit_count", 0)
            gc = result.get("green_coverage", 0)
            lcolor = result.get("leaf_color_stage", "")
            fmat = result.get("fruit_maturity", "")
            mode = result.get("detect_mode", "")
            saved = "saved" if persist else "not saved (single-shot)"
            write_log(f"[{ts}] L={lc} F={fc} G={gc}% Leaf={lcolor} Fruit={fmat} Mode={mode} ({saved})")
            history_log.appendleft(result)

            # Use masks from result for histogram and overlay
            leaf_mask = result.get("leaf_mask")
            fruit_mask = result.get("fruit_mask")
            fg_mask = result.get("fg_mask")

            # Build preview with optional mask overlay
            preview_img = cv2.imread(str(output_path))
            if preview_img is not None:
                if show_leaf_mask.get() and leaf_mask is not None:
                    green_overlay = np.zeros_like(preview_img)
                    green_overlay[:, :, 1] = 180
                    preview_img = cv2.addWeighted(preview_img, 0.7,
                                                   cv2.bitwise_and(green_overlay, green_overlay, mask=leaf_mask), 0.3, 0)
                if show_fruit_mask.get() and fruit_mask is not None:
                    orange_overlay = np.zeros_like(preview_img)
                    orange_overlay[:, :, 1] = 140
                    orange_overlay[:, :, 2] = 200
                    preview_img = cv2.addWeighted(preview_img, 0.7,
                                                   cv2.bitwise_and(orange_overlay, orange_overlay, mask=fruit_mask), 0.3, 0)
                if show_fg_mask.get() and fg_mask is not None:
                    blue_overlay = np.zeros_like(preview_img)
                    blue_overlay[:, :, 0] = 200
                    fg_3ch = cv2.merge([fg_mask, fg_mask, fg_mask])
                    preview_img = cv2.addWeighted(preview_img, 0.7,
                                                   cv2.bitwise_and(blue_overlay, blue_overlay, mask=fg_mask), 0.3, 0)
                show_preview_cv(preview_img)
            else:
                show_preview_cv(cv2.imread(str(output_path)))

            draw_hue_histogram(image_bgr, leaf_mask, fruit_mask)
            remember_hist(image_bgr, leaf_mask, fruit_mask)
            refresh_history()
            if mode_var.get() == "experiment":
                refresh_trend()
        root.after(0, _update)

    def choose_file():
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff")])
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            write_log("ERROR: Cannot read image — file may be corrupt or unsupported format")
            write_log("HINT: Use .jpg, .png, or .bmp files.")
            return
        nonlocal current_image_bgr
        current_image_bgr = img
        show_preview_cv(img)
        run_in_background(lambda: do_analyze(img, "file", path))

    def choose_video():
        path = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv")])
        if not path:
            return
        write_log(f"Opening video: {path}")

        def _work():
            set_status("Analysing video...")
            cancel_event.clear()
            try:
                va = VideoAnalyzer(analyzer, config, store=store)
                def on_progress(done, total, frame_result):
                    set_status(f"Video: {done}/{total} frames")
                summary = va.analyze_video(path, str(Path(args.output) / "video"),
                                           progress_callback=on_progress, persist=True)
                def _update():
                    set_status("Video complete")
                    analyzed = summary.get("analyzed_frames", 0)
                    lavg = summary.get("leaf_count_avg", 0)
                    favg = summary.get("fruit_count_avg", 0)
                    gc_avg = summary.get("green_coverage_avg", 0)
                    dur = summary.get("duration_sec", 0)
                    tree_ids = summary.get("tree_ids", [])
                    tree_txt = f"  Trees: {', '.join(tree_ids)}" if tree_ids else ""
                    write_log(f"Video done: {analyzed} frames, avg leaves={lavg} fruits={favg} "
                              f"green={gc_avg}% duration={dur}s{tree_txt}")
                    # Use the last frame's full result for the detail panel.
                    last = va.timeline[-1] if va.timeline else {}
                    update_results({
                        "leaf_count": f"avg {lavg}",
                        "fruit_count": f"avg {favg}",
                        "green_coverage": gc_avg,
                        "fruit_cover_pct": last.get("fruit_cover_pct", 0.0),
                        "leaf_color_stage": last.get("leaf_color_stage", "--"),
                        "leaf_senescence": last.get("leaf_senescence", "--"),
                        "leaf_avg_hue": last.get("leaf_avg_hue", 0.0),
                        "leaf_avg_saturation": last.get("leaf_avg_saturation", 0.0),
                        "leaf_confidence": last.get("leaf_confidence", 0.0),
                        "fruit_maturity": last.get("fruit_maturity", "--"),
                        "fruit_avg_hue": last.get("fruit_avg_hue", 0.0),
                        "fruit_confidence": last.get("fruit_confidence", 0.0),
                        "leaf_roughness": last.get("leaf_roughness", 0.0),
                        "leaf_curl_index": last.get("leaf_curl_index", 0.0),
                        "curled_leaf_pct": last.get("curled_leaf_pct", 0.0),
                        "wrinkled_fruit_count": last.get("wrinkled_fruit_count", 0),
                        "fruit_maturity_breakdown": last.get("fruit_maturity_breakdown", {}),
                        "fruit_wrinkle_summary": last.get("fruit_wrinkle_summary", {}),
                        "blur_level": last.get("blur_level", 0.0),
                        "tree_id": last.get("tree_id", ""),
                    })
                    timeline = va.timeline
                    if timeline:
                        draw_timeline(timeline)
                        remember_timeline(timeline)
                        notebook.select(timeline_frame)
                        ann_path = Path(args.output) / "video" / "annotated.mp4"
                        if ann_path.exists():
                            cap = cv2.VideoCapture(str(ann_path))
                            if cap.isOpened():
                                cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1))
                                ok, last_frame = cap.read()
                                cap.release()
                                if ok:
                                    show_preview_cv(last_frame)
                root.after(0, _update)
            except Exception as exc:
                write_log(f"Video ERROR [{type(exc).__name__}]: {exc}")
                write_log("HINT: Check that the video file is valid and not corrupted.")
            finally:
                root.after(0, lambda: progress.stop())
        run_in_background(_work)

    def capture_frame():
        def _work():
            set_status("Capturing camera...")
            try:
                img = capture_camera(args.camera, config["runtime"]["camera_warmup_frames"])
            except Exception as exc:
                write_log(f"Camera ERROR [{type(exc).__name__}]: {exc}")
                write_log("HINT: Check camera connection. Try Settings → Camera ID to change.")
                set_status("Camera error")
                return
            nonlocal current_image_bgr
            current_image_bgr = img
            root.after(0, lambda: show_preview_cv(img))
            do_analyze(img, f"camera:{args.camera}")
        run_in_background(_work)

    def show_recent_history():
        refresh_history()
        notebook.select(hist_frame)

    def save_settings():
        try:
            settings_path.write_text(json.dumps({"mode": mode_var.get()},
                                                ensure_ascii=False, indent=2),
                                     encoding="utf-8")
        except Exception as exc:
            write_log(f"WARN: could not save settings: {exc}")

    def refresh_trend():
        try:
            analysis = analyze_health_trend(store.recent(1_000_000), cfg=analyzer.config)
            report = _trend_text(analysis)
        except Exception as exc:
            report = f"ERROR: {exc}"
        def _do():
            trend_text.configure(state="normal")
            trend_text.delete("1.0", "end")
            trend_text.insert("1.0", report)
            trend_text.configure(state="disabled")
        root.after(0, _do)

    def show_trend():
        refresh_trend()
        notebook.select(trend_frame)

    def apply_mode():
        experiment = mode_var.get() == "experiment"
        btn_cam.configure(state="normal" if experiment else "disabled")
        btn_recent.configure(state="normal" if experiment else "disabled")
        btn_trend.configure(state="normal" if experiment else "disabled")
        lbl_mode.configure(text="Mode: Experiment" if experiment else "Mode: Single-shot")
        save_settings()
        if experiment:
            refresh_trend()

    def open_settings():
        win = tk.Toplevel(root)
        win.title("Settings - OliveVision")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(root)
        card = ttk.LabelFrame(win, text=" Application Mode ", style="Card.TLabelframe")
        card.pack(fill="x", padx=12, pady=12)
        for value, label, desc in (
            ("experiment", "Continuous experiment (recommended)",
             "Every capture / opened image is saved to the database so colour,\n"
             "wrinkle and fruit-count changes can be tracked over time (Trend tab)."),
            ("single", "Single image / video detection",
             "Analyse an image or video once. The result is shown but NOT saved\n"
             "to the database, so it will not affect the trend."),
        ):
            row = tk.Frame(card, bg=CARD)
            row.pack(fill="x", padx=8, pady=6)
            tk.Radiobutton(row, text=label, variable=mode_var, value=value,
                           command=apply_mode, bg=CARD, fg=TEXT,
                           activebackground=CARD, activeforeground=ACCENT,
                           selectcolor=BORDER, font=("Segoe UI", 10, "bold")).pack(anchor="w")
            tk.Label(row, text=desc, bg=CARD, fg=TEXT_DIM, justify="left",
                     font=("Segoe UI", 8)).pack(anchor="w", padx=(20, 4))
        info = ttk.Frame(win)
        info.pack(fill="x", padx=16, pady=(2, 8))
        ttk.Label(info, text=f"Database : {args.database}", style="Dim.TLabel").pack(anchor="w")
        ttk.Label(info, text=f"Output   : {args.output}", style="Dim.TLabel").pack(anchor="w")
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=(4, 12))
        win.update_idletasks()
        win.geometry(f"+{root.winfo_x() + 80}+{root.winfo_y() + 80}")
        win.grab_set()
        win.focus_set()

    # ========================================================== wire buttons
    btn_open.configure(command=choose_file)
    btn_cam.configure(command=capture_frame)
    btn_recent.configure(command=show_recent_history)
    btn_video.configure(command=choose_video)
    btn_reset.configure(command=reset_sliders)
    btn_trend.configure(command=show_trend)
    btn_settings.configure(command=open_settings)

    # ========================================================== canvas redraw
    # Cache the last chart inputs so charts can be re-rendered when their
    # tab becomes visible or the window is resized.
    hist_cache = {"image": None, "leaf": None, "fruit": None}

    def remember_hist(image_bgr, leaf_mask=None, fruit_mask=None):
        hist_cache["image"] = image_bgr
        hist_cache["leaf"] = leaf_mask
        hist_cache["fruit"] = fruit_mask

    def redraw_hist_if_needed(_event=None):
        if hist_cache["image"] is not None:
            draw_hue_histogram(hist_cache["image"], hist_cache["leaf"], hist_cache["fruit"])

    timeline_cache = {"data": None}

    def remember_timeline(data):
        timeline_cache["data"] = data

    def redraw_timeline_if_needed(_event=None):
        if timeline_cache["data"]:
            draw_timeline(timeline_cache["data"])

    hue_canvas.bind("<Configure>", redraw_hist_if_needed)
    timeline_canvas.bind("<Configure>", redraw_timeline_if_needed)

    # ========================================================== initial state
    write_log("OliveVision AI ready. Open an image or capture from camera.")
    refresh_history()
    apply_mode()
    write_log(f"Started in {'experiment' if mode_var.get() == 'experiment' else 'single-shot'} mode. "
              f"Switch it anytime via the Settings button.")

    root.mainloop()


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------
def list_trees(args):
    db_path = Path(args.database)
    if not db_path.exists():
        _error(f"Database not found: {db_path}",
               hint="Run 'analyze' or 'capture' first to create the database.")
    store = Store(args.database)
    ids = store.tree_ids()
    print(panel("Trial tree registry",
                f"  {bold('Total')}  {bold(str(len(ids)))} tree{'s' if len(ids) != 1 else ''}"))
    if not ids:
        print("  No tree IDs detected yet.")
        print("  Make sure QR codes are visible in captured images.")
        return
    print(f"  {'ID':<18} {'Observations':>12}   {'Last seen':>16}")
    print(f"  {dim(chr(9472)*18)} {dim(chr(9472)*12)}   {dim(chr(9472)*16)}")
    for tid in ids:
        tree_rows = store.recent_by_tree(tid)
        n = len(tree_rows)
        last = tree_rows[0]["observed_at"][:16].replace("T", " ") if tree_rows else "—"
        print(f"  {cyan(tid):<18} {bold(str(n)):>12}   {dim(last):>16}")


def soil(args):
    """Display soil moisture data from the UKK-KOSEN monitoring system."""
    try:
        client = SoilMoistureClient()
    except Exception as exc:
        _error(f"Failed to initialize soil moisture client: {exc}",
               hint="Check config/soil_moisture.yaml for correct API URL.")
    cmd = getattr(args, "soil_cmd", "latest")
    if cmd == "latest":
        data = client.get_latest()
        if data is None:
            print(panel("Soil Moisture - Latest", "  No data available."))
            return
        status = get_moisture_status(data)
        health = assess_moisture_health(data)
        s1 = data.get("sensor1_moisture_percent")
        s2 = data.get("sensor2_moisture_percent")
        ts = data.get("measured_at") or data.get("timestamp") or "—"
        lines = []
        lines.append(f"  {bold('Time')}       {ts}")
        lines.append(f"  {bold('Status')}     {_moisture_badge(status)}")
        if s1 is not None:
            lines.append(f"  {bold('Sensor 1')}   {s1:.1f}%")
        if s2 is not None:
            lines.append(f"  {bold('Sensor 2')}   {s2:.1f}%")
        if s1 is not None and s2 is not None:
            lines.append(f"  {bold('Average')}   {(s1 + s2) / 2:.1f}%")
        temp = data.get("temperature")
        hum = data.get("humidity")
        if temp is not None:
            lines.append(f"  {bold('Temp')}       {temp:.1f} C")
        if hum is not None:
            lines.append(f"  {bold('Humidity')}   {hum:.1f}%")
        lines.append(f"  {bold('Health')}    {health['message']}")
        lines.append(f"  {bold('Score')}     {health['score']:.2f}")
        print(panel("Soil Moisture - Latest", "\n".join(lines)))
    elif cmd == "history":
        hours = getattr(args, "hours", 24)
        records = client.get_history(hours=hours)
        if not records:
            print(panel("Soil Moisture - History", "  No history available."))
            return
        print(panel("Soil Moisture - History", f"  {bold(str(len(records)))} records (last {hours}h)"))
        for rec in records[:20]:
            ts = (rec.get("measured_at") or rec.get("timestamp") or "—")[:16]
            s1 = rec.get("sensor1_moisture_percent")
            s2 = rec.get("sensor2_moisture_percent")
            vals = [v for v in [s1, s2] if v is not None]
            avg = f"{sum(vals)/len(vals):.0f}%" if vals else "—"
            temp = rec.get("temperature")
            temp_str = f"{temp:.0f}C" if temp is not None else "—"
            print(f"  {dim(ts)}  avg={green(avg):>6}  temp={cyan(temp_str):>6}")
    elif cmd == "stats":
        hours = getattr(args, "hours", 24)
        stats = client.get_stats(hours=hours)
        if stats is None:
            print(panel("Soil Moisture - Stats", "  No stats available."))
            return
        lines = []
        lines.append(f"  {bold('Period')}       Last {hours} hours")
        lines.append(f"  {bold('Readings')}     {stats.get('total_readings', '?')}")
        for key, label in [("sensor1_avg", "Sensor 1 avg"), ("sensor2_avg", "Sensor 2 avg")]:
            v = stats.get(key)
            if v is not None:
                mn = stats.get(key.replace("_avg", "_min"), "?")
                mx = stats.get(key.replace("_avg", "_max"), "?")
                lines.append(f"  {bold(label + ':')}  {v:.1f}%  (min {mn:.1f}, max {mx:.1f})")
        print(panel("Soil Moisture - Stats", "\n".join(lines)))
    elif cmd == "status":
        data = client.get_latest()
        status = get_moisture_status(data)
        health = assess_moisture_health(data)
        s1 = data.get("sensor1_moisture_percent") if data else None
        s2 = data.get("sensor2_moisture_percent") if data else None
        vals = [v for v in [s1, s2] if v is not None]
        avg = f"{sum(vals)/len(vals):.1f}%" if vals else "—"
        print(f"  {_moisture_badge(status)}  avg={green(avg):>6}  "
              f"risk={_risk_color(health['risk'])}  score={health['score']:.2f}")


def _moisture_badge(status):
    """Return a colored badge for moisture status."""
    badges = {
        "dry": red("DRY"),
        "optimal": green("OPTIMAL"),
        "wet": yellow("WET"),
        "unknown": dim("UNKNOWN"),
    }
    return badges.get(status, dim(status.upper()))


def _risk_color(risk):
    """Return a colored risk string."""
    colors = {
        "critical": red,
        "high": accent_err,
        "moderate": yellow,
        "normal": green,
        "unknown": dim,
    }
    fn = colors.get(risk, dim)
    return fn(risk.upper())


def parser():
    common=argparse.ArgumentParser(add_help=False); common.add_argument("--config",default=str(ROOT/"config"/"runtime.yaml")); common.add_argument("--database",default=str(ROOT/"data"/"database"/"olivevision.db")); common.add_argument("--output",default=str(ROOT/"outputs"/"observations")); common.add_argument("--verbose",action="store_true"); common.add_argument("--upscale",action="store_true",help="AI-upscale low-resolution images before detection"); common.add_argument("--upscale-threshold",type=int,default=900,help="upscale images below this width/height (default 900)"); common.add_argument("--upscale-model",default="realesrgan-x4plus",help="upscale model (realesrgan-x4plus, realesr-animevideov3, realesrgan-x4plus-anime)"); common.add_argument("--upscale-scale",type=int,default=2,help="upscale ratio (2, 3, or 4; default 2)")
    p=argparse.ArgumentParser(description="OliveVision: Raspberry Pi friendly local olive monitoring"); sub=p.add_subparsers(dest="command",required=True)
    x=sub.add_parser("analyze",parents=[common],help="analyse one image and save its record"); x.add_argument("image"); x.add_argument("--explain",action="store_true",help="print a text explanation of why objects were detected"); x.add_argument("--diag",action="store_true",help="print pipeline diagnostics (rejections, signal coverage)"); x.add_argument("--no-soil-moisture",action="store_true",help="skip soil moisture integration"); x.add_argument("--drone",action="store_true",help="enable low-resolution (drone/aerial) detection mode"); x.set_defaults(func=analyze_file)
    x=sub.add_parser("capture",parents=[common],help="capture and analyse one camera frame"); x.add_argument("--camera",type=int,default=0); x.add_argument("--explain",action="store_true",help="print a text explanation of why objects were detected"); x.add_argument("--diag",action="store_true",help="print pipeline diagnostics (rejections, signal coverage)"); x.add_argument("--no-soil-moisture",action="store_true",help="skip soil moisture integration"); x.add_argument("--drone",action="store_true",help="enable low-resolution (drone/aerial) detection mode"); x.set_defaults(func=capture)
    x=sub.add_parser("monitor",parents=[common],help="periodically capture and analyse camera frames"); x.add_argument("--camera",type=int,default=0,help="camera device index (default 0)"); x.add_argument("--interval",type=int,default=3600,help="seconds between captures (default 3600)"); x.add_argument("--tree",type=str,default=None,help="associate observations with a trial tree ID"); x.add_argument("--limit",type=int,default=0,help="stop after N cycles (0 = unlimited)"); x.set_defaults(func=monitor)
    x=sub.add_parser("status",parents=[common],help="display latest local observations"); x.add_argument("--limit",type=int,default=20); x.add_argument("--tree",type=str,default=None,help="filter by trial tree ID (e.g. 第1試験樹)"); x.set_defaults(func=status)
    x=sub.add_parser("export",parents=[common],help="export the local database to CSV"); x.add_argument("csv"); x.set_defaults(func=export)
    x=sub.add_parser("trend",parents=[common],help="report colour/wrinkle health trends from stored observations"); x.add_argument("--limit",type=int,default=0,help="only use the most recent N observations (0 = all)"); x.add_argument("--tree",type=str,default=None,help="filter by trial tree ID (e.g. 第1試験樹)"); x.add_argument("--source",type=str,default=None,choices=["image","video"],help="filter by source type"); x.set_defaults(func=trend)
    x=sub.add_parser("trees",parents=[common],help="list all detected trial tree IDs"); x.set_defaults(func=list_trees)
    x=sub.add_parser("video",parents=[common],help="analyse an mp4/avi video frame by frame"); x.add_argument("video"); x.add_argument("--interval",type=int,default=10,help="analyse every Nth frame"); x.set_defaults(func=analyze_video_cli)
    x=sub.add_parser("soil",parents=[common],help="display soil moisture data"); x.add_argument("soil_cmd",nargs="?",default="latest",choices=["latest","history","stats","status"],help="soil moisture sub-command (default: latest)"); x.add_argument("--hours",type=int,default=24,help="hours of history to show (default 24)"); x.set_defaults(func=soil)
    x=sub.add_parser("gui",parents=[common],help="launch the local desktop GUI"); x.add_argument("--camera",type=int,default=0); x.set_defaults(func=gui)
    return p

if __name__=="__main__":
    args=parser().parse_args()
    try: args.func(args)
    except KeyboardInterrupt: print("Stopped safely.",file=sys.stderr); sys.exit(130)
    except SystemExit as exc:
        # _error() or other SystemExit with structured message.
        print(str(exc), file=sys.stderr)
        sys.exit(exc.code if isinstance(exc.code, int) else 1)
    except Exception as exc:
        print(f"\n{accent_err('ERROR')}  {type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"{dim('HINT')}  Run with --verbose for a full traceback.", file=sys.stderr)
        if args.verbose: traceback.print_exc()
        sys.exit(1)