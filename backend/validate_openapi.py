# C:\Users\86178\Desktop\云计算\大作业\backend\validate_openapi.py
import json
import yaml
from pathlib import Path
import jsonschema
import sys

# 定义项目根目录
PROJECT_ROOT = Path(r"C:\Users\86178\Desktop\云计算\大作业")

def get_paths():
    """获取所有文件路径"""
    paths = {
        "openapi": PROJECT_ROOT / "openapi.agent.yaml",
        "schema": PROJECT_ROOT / "graph.schema.json",
        "sample_mock": PROJECT_ROOT / "backend" / "mock_data" / "sample_graph.json",
        "backend_root": PROJECT_ROOT / "backend"
    }
    
    print("📂 文件路径检查:")
    for name, path in paths.items():
        exists = "✅" if path.exists() else "❌"
        print(f"  {exists} {name}: {path}")
    
    return paths

def validate_openapi_spec(paths):
    """验证A同学的OpenAPI文档格式"""
    print("\n📋 验证OpenAPI文档格式")
    print("=" * 50)
    
    if not paths["openapi"].exists():
        print(f"❌ 找不到OpenAPI文件: {paths['openapi']}")
        return False
    
    try:
        with open(paths["openapi"], 'r', encoding='utf-8') as f:
            openapi_spec = yaml.safe_load(f)
        
        # 基本检查
        print("1. 基本格式检查:")
        if openapi_spec.get("openapi") != "3.0.3":
            print(f"   ⚠️ OpenAPI版本不是3.0.3: {openapi_spec.get('openapi')}")
        else:
            print(f"   ✅ OpenAPI版本: 3.0.3")
        
        if "info" not in openapi_spec:
            print("   ❌ OpenAPI缺少info字段")
            return False
        else:
            title = openapi_spec["info"].get("title", "未知")
            print(f"   ✅ 标题: {title}")
        
        print("\n2. 接口路径检查:")
        if "paths" not in openapi_spec:
            print("   ❌ OpenAPI缺少paths字段")
            return False
        
        # 检查关键接口
        required_paths = ["/agent/v1/build", "/agent/v1/health"]
        all_paths = list(openapi_spec.get("paths", {}).keys())
        print(f"   发现{len(all_paths)}个接口: {all_paths}")
        
        for path in required_paths:
            if path in openapi_spec["paths"]:
                print(f"   ✅ 包含接口: {path}")
            else:
                print(f"   ❌ 缺少接口: {path}")
                return False
        
        print("\n3. Schema定义检查:")
        if "components" in openapi_spec and "schemas" in openapi_spec["components"]:
            schemas = list(openapi_spec["components"]["schemas"].keys())
            print(f"   发现{len(schemas)}个Schema: {schemas}")
            
            required_schemas = ["AgentBuildRequest", "GraphJSON", "ErrorResponse"]
            for schema in required_schemas:
                if schema in openapi_spec["components"]["schemas"]:
                    print(f"   ✅ 包含Schema: {schema}")
                else:
                    print(f"   ⚠️ 缺少Schema: {schema}")
        
        # 检查请求体示例
        print("\n4. 示例数据检查:")
        try:
            build_path = openapi_spec["paths"]["/agent/v1/build"]
            examples = build_path["post"]["requestBody"]["content"]["application/json"]["examples"]
            if "entropy" in examples:
                print("   ✅ 包含熵示例请求")
                example_data = examples["entropy"]["value"]
                print(f"     概念: {example_data.get('concept', 'N/A')}")
                print(f"     最大节点数: {example_data.get('constraints', {}).get('max_nodes', 'N/A')}")
            else:
                print("   ⚠️ 缺少熵示例请求")
        except KeyError:
            print("   ⚠️ 示例数据格式不完整")
        
        return True
        
    except yaml.YAMLError as e:
        print(f"❌ YAML解析错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 读取OpenAPI文件错误: {e}")
        return False

def validate_sample_data(paths):
    """验证Sample数据是否符合Schema"""
    print("\n📊 验证Sample数据")
    print("=" * 50)
    
    # 1. 读取Schema
    if not paths["schema"].exists():
        print(f"❌ 找不到Schema文件: {paths['schema']}")
        return False
    
    try:
        with open(paths["schema"], 'r', encoding='utf-8') as f:
            schema = json.load(f)
        print("✅ 成功读取Schema文件")
        print(f"   Schema版本: {schema.get('$schema', '未知')}")
        print(f"   Schema标题: {schema.get('title', '未知')}")
    except Exception as e:
        print(f"❌ 读取Schema失败: {e}")
        return False
    
    # 2. 读取你的Mock数据
    if not paths["sample_mock"].exists():
        print(f"❌ 找不到Mock文件: {paths['sample_mock']}")
        return False
    
    try:
        with open(paths["sample_mock"], 'r', encoding='utf-8') as f:
            mock_data = json.load(f)
        print("✅ 成功读取Mock数据")
    except Exception as e:
        print(f"❌ 读取Mock数据失败: {e}")
        return False
    
    # 3. 验证Schema
    try:
        jsonschema.validate(instance=mock_data, schema=schema)
        print("✅ Mock数据通过Schema验证")
        
        # 详细检查字段
        print("\n🔍 Mock数据详细检查:")
        meta = mock_data.get('meta', {})
        print(f"   核心概念: {meta.get('core_concept', 'N/A')}")
        print(f"   学科域: {meta.get('domains', [])}")
        print(f"   版本: {meta.get('version', 'N/A')}")
        print(f"   节点数: {len(mock_data.get('nodes', []))}")
        print(f"   边数: {len(mock_data.get('edges', []))}")
        print(f"   生成时间: {meta.get('generated_at', 'N/A')}")
        
        # 检查节点结构
        if mock_data.get("nodes"):
            first_node = mock_data["nodes"][0]
            required_fields = ["id", "label", "field", "type"]
            missing = [f for f in required_fields if f not in first_node]
            if not missing:
                print(f"   节点结构: ✅ 包含必要字段: {required_fields}")
            else:
                print(f"   节点结构: ❌ 缺少字段: {missing}")
        
        # 检查边结构
        if mock_data.get("edges"):
            first_edge = mock_data["edges"][0]
            required_fields = ["source", "target", "relation", "confidence", "evidence"]
            missing = [f for f in required_fields if f not in first_edge]
            if not missing:
                print(f"   边结构: ✅ 包含必要字段: {required_fields}")
            else:
                print(f"   边结构: ❌ 缺少字段: {missing}")
        
        return True
        
    except jsonschema.ValidationError as e:
        print(f"❌ Schema验证失败: {e.message}")
        print(f"   错误路径: {e.json_path}")
        print(f"   错误值: {e.instance}")
        return False
    except Exception as e:
        print(f"❌ 验证过程错误: {e}")
        return False

def check_openapi_request_format():
    """检查OpenAPI中的请求格式是否符合Agent要求"""
    print("\n📨 检查OpenAPI请求格式")
    print("=" * 50)
    
    try:
        openapi_path = PROJECT_ROOT / "openapi.agent.yaml"
        with open(openapi_path, 'r', encoding='utf-8') as f:
            openapi_spec = yaml.safe_load(f)
        
        # 提取AgentBuildRequest Schema
        if "components" in openapi_spec and "schemas" in openapi_spec["components"]:
            agent_request = openapi_spec["components"]["schemas"].get("AgentBuildRequest", {})
            
            if not agent_request:
                print("❌ 找不到AgentBuildRequest Schema")
                return False
            
            print("✅ 找到AgentBuildRequest Schema")
            
            # 检查必需字段
            required_fields = agent_request.get("required", [])
            print(f"   必需字段: {required_fields}")
            
            # 检查concept字段
            properties = agent_request.get("properties", {})
            concept_field = properties.get("concept", {})
            if concept_field:
                print(f"   concept字段:")
                print(f"     最小长度: {concept_field.get('minLength', 'N/A')}")
                print(f"     最大长度: {concept_field.get('maxLength', 'N/A')}")
            
            # 检查constraints字段
            constraints = properties.get("constraints", {})
            if constraints:
                print(f"   constraints字段:")
                constraints_props = constraints.get("properties", {})
                if "domains" in constraints_props:
                    domain_enum = constraints_props["domains"].get("items", {}).get("enum", [])
                    print(f"     学科域枚举: {domain_enum}")
                if "max_nodes" in constraints_props:
                    print(f"     最大节点数: {constraints_props['max_nodes'].get('example', 'N/A')}")
            
            # 检查示例请求
            try:
                example = openapi_spec["paths"]["/agent/v1/build"]["post"]["requestBody"]["content"]["application/json"]["examples"]["entropy"]["value"]
                print(f"\n✅ 示例请求格式:")
                print(f"   概念: {example.get('concept', 'N/A')}")
                print(f"   学科域: {example.get('constraints', {}).get('domains', [])}")
                print(f"   最大节点: {example.get('constraints', {}).get('max_nodes', 'N/A')}")
                print(f"   最小置信度: {example.get('constraints', {}).get('min_confidence', 'N/A')}")
            except KeyError:
                print("⚠️ 示例请求不完整")
            
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ 检查OpenAPI请求格式失败: {e}")
        return False

def compare_with_generate_mock():
    """比较OpenAPI示例与你的generate_mock_graph输出"""
    print("\n🔄 比较数据格式")
    print("=" * 50)
    
    try:
        # 添加backend到Python路径
        sys.path.append(str(PROJECT_ROOT / "backend"))
        
        # 导入你的GraphService
        from app.services.graph_service import GraphService
        
        service = GraphService()
        
        # 生成测试数据
        test_concept = "熵"
        mock_data = service.generate_mock_graph(test_concept)
        
        print(f"1. 你的generate_mock_graph输出:")
        print(f"   概念: {mock_data.get('meta', {}).get('core_concept', 'N/A')}")
        print(f"   版本: {mock_data.get('meta', {}).get('version', 'N/A')}")
        print(f"   节点数: {len(mock_data.get('nodes', []))}")
        print(f"   边数: {len(mock_data.get('edges', []))}")
        
        # 读取你的Mock文件
        mock_file = PROJECT_ROOT / "backend" / "mock_data" / "sample_graph.json"
        if mock_file.exists():
            with open(mock_file, 'r', encoding='utf-8') as f:
                file_mock = json.load(f)
            
            print(f"\n2. Mock文件数据:")
            print(f"   概念: {file_mock.get('meta', {}).get('core_concept', 'N/A')}")
            print(f"   版本: {file_mock.get('meta', {}).get('version', 'N/A')}")
            print(f"   节点数: {len(file_mock.get('nodes', []))}")
            print(f"   边数: {len(file_mock.get('edges', []))}")
            
            # 对比字段
            print(f"\n3. 字段对比:")
            mock_fields = set(mock_data.keys())
            file_fields = set(file_mock.keys())
            
            if mock_fields == file_fields:
                print("   ✅ 顶层字段一致")
            else:
                print("   ⚠️ 顶层字段不一致:")
                print(f"      函数有但文件无: {mock_fields - file_fields}")
                print(f"      文件有但函数无: {file_fields - mock_fields}")
        
        # 验证Schema
        from app.core.schema import validator
        is_valid, message = validator.validate(mock_data)
        
        if is_valid:
            print(f"\n4. Schema验证: ✅ 通过")
        else:
            print(f"\n4. Schema验证: ❌ 失败 - {message}")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("   确保在backend目录运行: python validate_openapi.py")
        return False
    except Exception as e:
        print(f"❌ 比较失败: {e}")
        return False

def generate_test_report():
    """生成测试报告"""
    print("\n" + "=" * 60)
    print("🎯 A同学OpenAPI和Mock数据验证")
    print("=" * 60)
    
    # 获取路径
    paths = get_paths()
    
    # 检查必要文件
    missing_files = []
    for name, path in paths.items():
        if not path.exists():
            missing_files.append(f"{name}: {path}")
    
    if missing_files:
        print("\n❌ 缺少必要文件:")
        for missing in missing_files:
            print(f"   {missing}")
        return False
    
    print("\n✅ 所有必要文件都存在")
    
    # 运行所有测试
    tests = [
        ("OpenAPI文档验证", lambda: validate_openapi_spec(paths)),
        ("Mock数据Schema验证", lambda: validate_sample_data(paths)),
        ("OpenAPI请求格式检查", check_openapi_request_format),
        ("数据格式对比", compare_with_generate_mock)
    ]
    
    report = {
        "测试时间": "2025-01-19",
        "测试目标": "验证A同学的OpenAPI和Mock数据",
        "文件路径": {k: str(v) for k, v in paths.items()},
        "结果": {}
    }
    
    all_passed = True
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🔍 {test_name}")
        print(f"{'='*50}")
        
        try:
            result = test_func()
            status = "通过" if result else "失败"
            report["结果"][test_name] = status
            
            if result:
                print(f"✅ {test_name}: 通过")
            else:
                print(f"❌ {test_name}: 失败")
                all_passed = False
        except Exception as e:
            report["结果"][test_name] = f"异常: {str(e)}"
            print(f"❌ {test_name}: 异常 - {e}")
            all_passed = False
            import traceback
            traceback.print_exc()
    
    # 保存报告
    try:
        report_path = PROJECT_ROOT / "backend" / "validation_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n📁 测试报告已保存到: {report_path}")
    except Exception as e:
        print(f"\n⚠️ 无法保存报告: {e}")
    
    # 最终总结
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！")
        print("✅ OpenAPI文档格式正确")
        print("✅ Mock数据符合Schema")
        print("✅ 请求格式符合要求")
        print("✅ 数据格式兼容")
    else:
        print("⚠️ 部分测试失败，请检查问题")
    
    print("=" * 60)
    
    print("\n💡 测试总结:")
    print(f"1. OpenAPI文档位置: {paths['openapi']}")
    print(f"2. Schema文件位置: {paths['schema']}")
    print(f"3. Mock数据位置: {paths['sample_mock']}")
    print(f"4. Backend位置: {paths['backend_root']}")
    
    return all_passed

if __name__ == "__main__":
    # 检查是否安装了yaml
    try:
        import yaml
    except ImportError:
        print("❌ 缺少yaml库，请安装: pip install pyyaml")
        print("运行: pip install pyyaml jsonschema")
        exit(1)
    
    # 运行测试
    success = generate_test_report()
    
    if success:
        print("\n🚀 下一步:")
        print("1. 告诉A同学所有测试通过")
        print("2. 可以开始集成真正的Agent服务")
        print("3. 修改config.py: USE_MOCK = False")
        print("4. 修改graph_service.py调用Agent API")
    else:
        print("\n🔧 发现问题:")
        print("1. 检查OpenAPI文档格式")
        print("2. 检查Mock数据是否符合Schema")
        print("3. 检查文件路径是否正确")
        print("4. 修复问题后重新运行测试")
    
    exit(0 if success else 1)