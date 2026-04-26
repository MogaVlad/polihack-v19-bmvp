import sys
from engine.conversation import ConversationManager
from models.agent_definition import AgentDefinition
from models.chat import ChatMessage

agent = AgentDefinition(id="test", name="Test", goal="Test goal", inputs=[], outputs=[])
cm = ConversationManager(agent)
cm.initialize("system prompt", "hello")
print("is_active:", cm.is_active)
resp = cm.followup("my first question")
print("resp:", resp)
cm.history.pop() # remove agent response
cm.history.append(ChatMessage(role="agent", content="[Error: timed out]"))
print("History before retry:")
for m in cm.history: print(m.role, m.content)

print("retrying...")
resp2 = cm.retry_last_followup()
print("resp2:", resp2)
print("History after retry:")
for m in cm.history: print(m.role, m.content)
