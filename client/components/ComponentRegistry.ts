/**
 * Component Registry - 用于注册和管理自定义UI组件
 */

/**
 * 组件属性接口
 */
export interface ComponentProps<T = any> {
  state: T;
  onAction?: (actionId: string, params: Record<string, any>) => void;
}

/**
 * 组件注册表
 */
class ComponentRegistry {
  private components: Map<string, any> = new Map();

  /**
   * 注册组件
   */
  register(name: string, component: any) {
    this.components.set(name, component);
  }

  /**
   * 获取组件
   */
  get(name: string) {
    return this.components.get(name);
  }

  /**
   * 检查组件是否存在
   */
  has(name: string) {
    return this.components.has(name);
  }

  /**
   * 获取所有组件名称
   */
  getComponentNames() {
    return Array.from(this.components.keys());
  }
}

// 创建全局单例
export const componentRegistry = new ComponentRegistry();

// 导出默认实例
export default componentRegistry;