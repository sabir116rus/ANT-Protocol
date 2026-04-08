import json
import io

with io.open("architecture/n8n_workflow_mvp.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 1. Update Auth Check to use String()
for n in data['nodes']:
    if n['name'] == 'Auth Check':
        n['parameters']['conditions']['conditions'][0]['leftValue'] = '={{ String($json.chat_id) }}'
        n['parameters']['conditions']['conditions'][0]['rightValue'] = '={{ String($env.TELEGRAM_CHAT_ID) }}'

# 2. Update date formats in Format Add and Format List
for n in data['nodes']:
    if n['name'] == 'Format Add':
        code = n['parameters']['jsCode']
        code = code.replace("`✅ Задача добавлена\\n\\n${priorityEmoji[t.priority] || '🟡'} ${t.title}\\n📅 ${t.task_date}\\n⏱ ${t.estimated_minutes} мин`;", 
                            "\\nconst dAdd = t.task_date ? t.task_date.split('-') : [];\\nconst fDateAdd = dAdd.length === 3 ? `${dAdd[2]}.${dAdd[1]}.${dAdd[0]}` : t.task_date;\\n\\nconst text = `✅ Задача добавлена\\n\\n${priorityEmoji[t.priority] || '🟡'} ${t.title}\\n📅 ${fDateAdd}\\n⏱ ${t.estimated_minutes} мин`;")
        n['parameters']['jsCode'] = code
        
    if n['name'] == 'Format List':
        code = n['parameters']['jsCode']
        code = code.replace("let lines = [`📋 Задачи на ${resp.task_date}\\n`];",
                            "const dList = resp.task_date ? resp.task_date.split('-') : [];\\nconst fDateList = dList.length === 3 ? `${dList[2]}.${dList[1]}.${dList[0]}` : resp.task_date;\\n\\nlet lines = [`📋 Задачи на ${fDateList}\\n`];")
        n['parameters']['jsCode'] = code

# 3. Add Empty args validation
main_conns = data['connections']['Command Router']['main']
main_conns[0] = [{'node': 'Check Add Args', 'type': 'main', 'index': 0}]

data['connections']['Check Add Args'] = {
    'main': [
        [{'node': 'HTTP Add Task', 'type': 'main', 'index': 0}],
        [{'node': 'Format Add Error', 'type': 'main', 'index': 0}]
    ]
}

data['connections']['Format Add Error'] = {
    'main': [
        [{'node': 'Send Response', 'type': 'main', 'index': 0}]
    ]
}

data['nodes'].append({
    'parameters': {
        'conditions': {
            'options': { 'caseSensitive': True },
            'conditions': [
                {
                    'id': 'args-not-empty',
                    'leftValue': '={{ $json.args }}',
                    'rightValue': '',
                    'operator': { 'type': 'string', 'operation': 'notEmpty' }
                }
            ],
            'combinator': 'and'
        }
    },
    'id': 'a1b2c3d4-0001-0001-0001-000000000013',
    'name': 'Check Add Args',
    'type': 'n8n-nodes-base.if',
    'typeVersion': 2,
    'position': [1000, 50]
})

data['nodes'].append({
    'parameters': {
        'jsCode': "const chatId = $('Parse Command').first().json.chat_id;\nreturn [{ json: { chat_id: chatId, text: '❌ После /add укажите название задачи' } }];"
    },
    'id': 'a1b2c3d4-0001-0001-0001-000000000014',
    'name': 'Format Add Error',
    'type': 'n8n-nodes-base.code',
    'typeVersion': 2,
    'position': [1200, -50]
})

with io.open("architecture/n8n_workflow_mvp.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
