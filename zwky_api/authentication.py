from rest_framework.authentication import SessionAuthentication

class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    自定义会话认证类，豁免CSRF验证
    
    REST Framework默认的SessionAuthentication会执行CSRF验证，
    对于一些API场景（如移动应用），我们可能希望绕过这一验证。
    
    注意：这会降低安全性，请确保你了解潜在风险。
    理想情况下，应该使用JWT或其他token认证方式替代。
    """
    
    def enforce_csrf(self, request):
        """
        重写方法以禁用CSRF验证
        """
        # 不执行CSRF验证
        return 