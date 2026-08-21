"""Source contract for visible task-deletion errors in the confirmation modal."""

from pathlib import Path


def main() -> None:
    source = Path("frontend/src/App.jsx").read_text(encoding="utf-8")
    styles = Path("frontend/src/styles.css").read_text(encoding="utf-8")

    # Cases A-B: HTTP 500/404 messages flow through parseResponse into the modal alert.
    assert 'const [deleteTaskError, setDeleteTaskError] = useState("")' in source
    assert 'await parseResponse(response, "删除历史方案")' in source
    assert "setDeleteTaskError(message.startsWith(\"删除历史方案失败\")" in source
    assert '{deleteTaskError && (' in source
    assert 'className="delete-task-error" role="alert"' in source
    assert "⚠ 删除失败原因" in source
    assert "<p>{deleteTaskError}</p>" in source

    # Case C: success clears the error, closes the modal, and removes the task locally.
    success_start = source.index("setRecentTasks((current) => current.filter")
    success_end = source.index("} catch (requestError)", success_start)
    success = source[success_start:success_end]
    assert 'setDeleteTaskError("")' in success
    assert "setTaskPendingDeletion(null)" in success

    # Case D: both cancel paths clear the dedicated error before closing.
    assert source.count('setDeleteTaskError(""); setTaskPendingDeletion(null)') >= 2
    assert ".delete-task-error" in styles
    assert "#fff2f2" in styles and "#a82f2f" in styles

    print("Cases A-B: 404/500 errors remain visible inside the modal")
    print("Case C: successful deletion closes and updates history")
    print("Case D: cancel and backdrop dismissal clear deletion errors")


if __name__ == "__main__":
    main()
