import React from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  FileText,
  SendToBack,
  Settings,
  Zap,
  MessageSquare,
} from "lucide-react";

const Navigation: React.FC = () => {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname.startsWith(path)
      ? "bg-indigo-50 text-indigo-700 font-semibold"
      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900";
  };

  const navItems = [
    { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
    { name: "Contacts", path: "/contacts", icon: Users },
    { name: "Campaigns", path: "/campaigns", icon: SendToBack },
  ];

  const contentItems = [
    { name: "Templates", path: "/templates", icon: FileText },
    { name: "Quick Replies", path: "/quick-replies", icon: Zap },
  ];

  const configItems = [
    { name: "Settings", path: "/settings", icon: Settings },
  ];

  const NavItem = ({ item }: { item: any }) => (
    <Link
      to={item.path}
      className={`group flex items-center px-4 py-2.5 text-sm rounded-lg transition-all duration-200 ${isActive(
        item.path
      )}`}
    >
      <item.icon
        className={`mr-3 h-5 w-5 transition-colors ${location.pathname.startsWith(item.path)
          ? "text-indigo-600"
          : "text-gray-400 group-hover:text-gray-500"
          }`}
      />
      {item.name}
    </Link>
  );

  return (
    <div className="flex flex-col flex-shrink-0 w-64 h-full bg-white border-r border-gray-200">
      {/* Logo Area */}
      <div className="flex items-center h-16 flex-shrink-0 px-6 bg-white border-b border-gray-100">
        <div className="flex items-center gap-2 text-indigo-600">
          <span className="text-lg font-bold tracking-tight text-gray-900">Golden Cars CRM</span>
        </div>
      </div>

      {/* Nav Content */}
      <div className="flex-1 flex flex-col overflow-y-auto px-3 py-6 space-y-8">

        {/* Main Section */}
        <div className="space-y-1">
          <h3 className="px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Main</h3>
          {navItems.map((item) => (
            <NavItem key={item.path} item={item} />
          ))}
        </div>

        {/* Content Section */}
        <div className="space-y-1">
          <h3 className="px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Content</h3>
          {contentItems.map((item) => (
            <NavItem key={item.path} item={item} />
          ))}
        </div>

        {/* Configuration Section */}
        <div className="space-y-1">
          <h3 className="px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">System</h3>
          {configItems.map((item) => (
            <NavItem key={item.path} item={item} />
          ))}
        </div>
      </div>
    </div>
  );
};
export default Navigation;
