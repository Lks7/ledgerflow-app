import uuid
from datetime import date, datetime

from .models import TodoItem


def list_todos(status="", quadrant="", category=""):
    """List todos with optional filters."""
    qs = TodoItem.objects.all()
    if status:
        qs = qs.filter(status=status)
    if quadrant:
        qs = qs.filter(quadrant=quadrant)
    if category:
        qs = qs.filter(category=category)
    return list(qs.values())


def create_todo(title, quadrant="q1", category="other", due_date="", note=""):
    """Create a new todo item."""
    title = (title or "").strip()
    if not title:
        return None, "标题不能为空"

    if quadrant not in ("q1", "q2", "q3", "q4"):
        quadrant = "q1"

    item = TodoItem(
        id=str(uuid.uuid4()),
        title=title,
        quadrant=quadrant,
        category=category or "other",
        note=note or "",
    )

    if due_date:
        try:
            item.due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass

    # Sort order: newest on top within quadrant
    max_order = TodoItem.objects.filter(quadrant=quadrant).count()
    item.sort_order = max_order
    item.save()
    return item, None


def update_todo(item_id, title, quadrant, category, due_date, note):
    """Update an existing todo item."""
    try:
        item = TodoItem.objects.get(id=item_id)
    except TodoItem.DoesNotExist:
        return False

    title = (title or "").strip()
    if title:
        item.title = title
    if quadrant in ("q1", "q2", "q3", "q4"):
        item.quadrant = quadrant
    if category:
        item.category = category
    item.note = note or ""

    if due_date:
        try:
            item.due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass
    else:
        item.due_date = None

    item.save()
    return True


def toggle_todo(item_id):
    """Toggle todo status between pending and done."""
    try:
        item = TodoItem.objects.get(id=item_id)
    except TodoItem.DoesNotExist:
        return False

    if item.status == "done":
        item.status = "pending"
        item.completed_at = None
    else:
        item.status = "done"
        item.completed_at = datetime.now()

    item.save()
    return True


def delete_todo(item_id):
    """Delete a todo item."""
    TodoItem.objects.filter(id=item_id).delete()


def move_quadrant(item_id, quadrant):
    """Move a todo to a different quadrant."""
    if quadrant not in ("q1", "q2", "q3", "q4"):
        return False
    try:
        item = TodoItem.objects.get(id=item_id)
    except TodoItem.DoesNotExist:
        return False

    item.quadrant = quadrant
    item.save()
    return True


def todo_summary():
    """Return summary statistics for the todo dashboard."""
    today = date.today()
    all_items = TodoItem.objects.all()

    total = all_items.count()
    pending = all_items.filter(status="pending").count()
    done = all_items.filter(status="done").count()
    due_today = all_items.filter(status="pending", due_date=today).count()
    overdue = all_items.filter(status="pending", due_date__lt=today).exclude(
        due_date=None
    ).count()

    # Per-quadrant counts (pending only)
    q1 = all_items.filter(status="pending", quadrant="q1").count()
    q2 = all_items.filter(status="pending", quadrant="q2").count()
    q3 = all_items.filter(status="pending", quadrant="q3").count()
    q4 = all_items.filter(status="pending", quadrant="q4").count()

    return {
        "total": total,
        "pending": pending,
        "done": done,
        "due_today": due_today,
        "overdue": overdue,
        "q1": q1,
        "q2": q2,
        "q3": q3,
        "q4": q4,
    }
