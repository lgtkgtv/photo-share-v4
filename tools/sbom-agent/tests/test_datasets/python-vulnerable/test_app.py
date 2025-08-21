#!/usr/bin/env python3
"""
Test Python Application for Vulnerability Scanning
==================================================

Simple Python application that imports vulnerable packages for testing
the SBOM Agent's ability to detect vulnerabilities in real code.

⚠️ WARNING: This application imports vulnerable packages and should
only be used in isolated test environments.
"""

# Import vulnerable packages to test detection
try:
    import jinja2
    print(f"✓ Jinja2 {jinja2.__version__} imported")
except ImportError:
    print("✗ Jinja2 not available")

try:
    import yaml
    print(f"✓ PyYAML imported")  
except ImportError:
    print("✗ PyYAML not available")

try:
    import requests
    print(f"✓ Requests {requests.__version__} imported")
except ImportError:
    print("✗ Requests not available")

try:
    import flask
    print(f"✓ Flask {flask.__version__} imported")
except ImportError:
    print("✗ Flask not available")

try:
    import django
    print(f"✓ Django {django.__version__} imported")
except ImportError:
    print("✗ Django not available")


def vulnerable_template_example():
    """Example of potentially vulnerable template usage."""
    try:
        from jinja2 import Template
        
        # This would be vulnerable in older Jinja2 versions
        template = Template("Hello {{ name }}!")
        result = template.render(name="World")
        print(f"Template result: {result}")
        
        return result
    except Exception as e:
        print(f"Template example failed: {e}")
        return None


def vulnerable_yaml_example():
    """Example of potentially vulnerable YAML usage."""
    try:
        import yaml
        
        # This would be vulnerable in older PyYAML versions
        yaml_data = """
        message: "Hello World"
        numbers: [1, 2, 3]
        """
        
        # Using safe_load (secure) vs load (potentially vulnerable)
        data = yaml.safe_load(yaml_data)
        print(f"YAML data: {data}")
        
        return data
    except Exception as e:
        print(f"YAML example failed: {e}")
        return None


def vulnerable_request_example():
    """Example of potentially vulnerable HTTP request."""
    try:
        import requests
        
        # This would be vulnerable in older requests versions
        # due to certificate verification issues
        response = requests.get("https://httpbin.org/json", verify=True)
        print(f"Request status: {response.status_code}")
        
        return response.status_code
    except Exception as e:
        print(f"Request example failed: {e}")
        return None


def main():
    """Run vulnerability test examples."""
    print("🧪 Testing Vulnerable Package Imports")
    print("=" * 50)
    
    print("\n📋 Import Test Results:")
    
    print("\n🌐 Template Processing Test:")
    vulnerable_template_example()
    
    print("\n📄 YAML Processing Test:")
    vulnerable_yaml_example()
    
    print("\n🌍 HTTP Request Test:")
    vulnerable_request_example()
    
    print("\n" + "=" * 50)
    print("⚠️  This application contains vulnerable packages")
    print("   Use only for security testing purposes")
    print("   Run SBOM Agent to detect vulnerabilities:")
    print("   python tools/sbom-agent/src/cli.py analyze . --scan-vulnerabilities")


if __name__ == "__main__":
    main()