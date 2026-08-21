"""Static UI contract checks for generation controls and progress placement."""

from pathlib import Path


def main() -> None:
    source = Path("frontend/src/App.jsx").read_text(encoding="utf-8")

    assert 'className="generation-options"' not in source
    assert 'className="task-progress"' not in source
    assert 'aria-label="任务生成进度"' not in source
    assert 'generation_options: selectedGenerationOptions' not in source

    report_button = "查看方案报告</button>"
    assert report_button in source
    assert "generationOptions.generate_report &&" not in source
    assert 'key === "solution" && productFlow &&' in source
    assert "generationOptions.generate_flow && productFlow" not in source

    assert "生成交互原型" in source
    assert 'className="plan-artifacts"' in source
    assert "附加产物" in source
    assert "等待你补充信息" in source
    assert "prototypeProgress?.percent" in source

    print("Generation UI contract: passed")


if __name__ == "__main__":
    main()
