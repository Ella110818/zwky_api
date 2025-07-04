import requests

def get_token(username, password):
    url = 'http://localhost:8000/api/user/login/'
    data = {
        'username': username,
        'password': password
    }
    
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        result = response.json()
        
        # 检查API的返回格式
        if result.get('code') == 200 and result.get('data'):
            return result['data']
        else:
            print(f"API返回错误: {result.get('message', '未知错误')}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if hasattr(response, 'text'):
            print(f"Response: {response.text}")
        return None

if __name__ == '__main__':
    # 使用提供的凭据
    result = get_token('韩石', 'hd123456')
    if result:
        print("\nToken获取成功！")
        print("\n访问令牌 (Access Token):")
        print("Bearer", result.get('token', '获取失败'))  # API返回token而不是access
        if 'refresh' in result:
            print("\n刷新令牌 (Refresh Token):")
            print(result['refresh'])
        print("\n用户信息:")
        print(f"用户ID: {result.get('userId')}")
        print(f"用户名: {result.get('username')}")
        print(f"角色: {result.get('role')}")
    else:
        print("\n获取token失败。请检查用户名和密码是否正确。") 