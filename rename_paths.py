import os, re

agents = {
    "legal_agent": "legal_src",
    "stock_agent": "stock_src"
}

base = "agents"

for agent, new_name in agents.items():
    agent_path = os.path.join(base, agent)

    # 폴더 이름 변경
    old_dir = os.path.join(agent_path, "src")
    new_dir = os.path.join(agent_path, new_name)

    if os.path.exists(old_dir):
        os.rename(old_dir, new_dir)
        print(f"폴더 rename: {old_dir} → {new_dir}")

    # 해당 agent 폴더 안 .py 파일 전부 치환
    for root, dirs, files in os.walk(agent_path):
        for file in files:
            if not file.endswith(".py"):
                continue
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding = "utf-8") as f:
                content = f.read()

            new_content = content

            # import 문
            new_content = re.sub(r'\bfrom src\.', f'from {new_name}.', new_content)
            new_content = re.sub(r'\bimport src\.', f'import {new_name}.', new_content)
            # -m 실행
            new_content = re.sub(r'-m src\.', f'-m {new_name}.', new_content)
            # 파일 경로 문자열
            new_content = new_content.replace('"src/', f'"{new_name}/')
            new_content = new_content.replace("'src/", f"'{new_name}/")

            # 파일 내용 치환
            if new_content != content:
                with open(filepath, "w", encoding = "utf-8") as f:
                    f.write(new_content)
                print(f"Modified: {filepath}")
