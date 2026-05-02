import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def sync_session_artifacts(session, exercise_name: str = None) -> None:
    """Sync session artifacts from sovereign-agent's internal directory to local sessions/ folder.

    Args:
        session: The session object returned by create_session.
        exercise_name: Optional name of the exercise to group sessions under.
    """
    try:
        src = Path(session.directory).resolve()
        # The local destination is sessions/<exercise_name>/<session_id>
        if exercise_name:
            dest = PROJECT_ROOT / "sessions" / exercise_name / session.session_id
        else:
            dest = PROJECT_ROOT / "sessions" / session.session_id

        if not src.exists():
            return

        # Create destination if it doesn't exist
        dest.mkdir(parents=True, exist_ok=True)

        for root, _dirs, files in os.walk(src):
            # Use os.path.relpath for better compatibility on Windows
            rel_path = os.path.relpath(root, str(src))
            target_dir = dest / rel_path

            for file in files:
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(os.path.join(root, file), target_dir / file)

        # Print relative to project root for cleaner output
        try:
            display_path = dest.relative_to(PROJECT_ROOT)
        except ValueError:
            display_path = dest
        print(f"[OK] Artifacts synced to: {display_path}")
    except Exception as e:
        print(f"[WARN] Failed to sync session artifacts: {e}")
