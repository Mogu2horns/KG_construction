from openai import OpenAI
import time

class QwenChat:
    def __init__(self, base_url="http://202.120.59.70:1234/v1/", api_key="wcf0326", model="Qwen3-8B"):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.conversation_history = []
        self.system_prompt = "你是一个有用的AI助手，请用中文回答用户的问题。"
        
        # 添加系统提示
        self.conversation_history.append({"role": "system", "content": self.system_prompt})
    
    def stream_chat(self, user_input):
        """流式对话"""
        # 添加用户输入到对话历史
        self.conversation_history.append({"role": "user", "content": user_input})
        
        print("\n🤖 AI: ", end="", flush=True)
        
        try:
            # 创建流式响应
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                stream=True,
                temperature=0.7,
                max_tokens=2048,
            )
            
            full_response = ""
            
            # 处理流式响应
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    print(content, end="", flush=True)
                    full_response += content
            
            print("\n")  # 对话结束后换行
            
            # 将AI回复添加到对话历史
            self.conversation_history.append({"role": "assistant", "content": full_response})
            
            return full_response
            
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            return None
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = [{"role": "system", "content": self.system_prompt}]
        print("🗑️  对话历史已清空")
    
    def show_history(self):
        """显示对话历史"""
        print("\n" + "="*50)
        print("📜 对话历史:")
        print("="*50)
        for i, msg in enumerate(self.conversation_history[1:], 1):  # 跳过system提示
            role_icon = "👤" if msg["role"] == "user" else "🤖"
            print(f"{role_icon} {msg['role']}: {msg['content']}")
            if i < len(self.conversation_history[1:]):
                print("-" * 30)
        print("="*50)
    
    def run_chat(self):
        """运行交互式对话"""
        print("🚀 Qwen3-8B 对话助手已启动！")
        print("💡 特殊命令:")
        print("   /clear - 清空对话历史")
        print("   /history - 显示对话历史") 
        print("   /quit - 退出对话")
        print("-" * 50)
        
        while True:
            try:
                # 获取用户输入
                user_input = input("\n👤 你: ").strip()
                
                # 处理特殊命令
                if user_input.lower() in ['/quit', '/exit', '退出', 'quit', 'exit']:
                    print("👋 再见！")
                    break
                elif user_input.lower() in ['/clear', '清空']:
                    self.clear_history()
                    continue
                elif user_input.lower() in ['/history', '历史']:
                    self.show_history()
                    continue
                elif user_input == '':
                    continue
                
                # 显示思考状态
                print("⏳ AI正在思考...", end="", flush=True)
                time.sleep(0.5)  # 让用户看到思考状态
                print("\r", end="", flush=True)  # 清除思考状态
                
                # 进行流式对话
                self.stream_chat(user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 对话被中断，再见！")
                break
            except Exception as e:
                print(f"\n❌ 发生错误: {e}")

# 使用示例
if __name__ == "__main__":
    # 创建聊天实例
    chat = QwenChat()
    
    # 开始对话
    chat.run_chat()