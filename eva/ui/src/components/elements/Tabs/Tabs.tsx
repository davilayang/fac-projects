import * as RadixTabs from "@radix-ui/react-tabs";
import type { ReactNode } from "react";
import "./Tabs.css";

export interface TabItem {
  id: string;
  label: string;
  content: ReactNode;
}

interface TabsProps {
  tabs: TabItem[];
  defaultTab?: string;
  className?: string;
}

export function Tabs({ tabs, defaultTab, className }: TabsProps) {
  const initial = defaultTab ?? tabs[0]?.id;

  return (
    <RadixTabs.Root
      className={["tabs", className].filter(Boolean).join(" ")}
      defaultValue={initial}
    >
      <RadixTabs.List className="tabs__list" aria-label="Tab navigation">
        {tabs.map((tab) => (
          <RadixTabs.Trigger
            key={tab.id}
            className="tabs__trigger"
            value={tab.id}
          >
            {tab.label}
          </RadixTabs.Trigger>
        ))}
      </RadixTabs.List>

      {tabs.map((tab) => (
        <RadixTabs.Content
          key={tab.id}
          className="tabs__content"
          value={tab.id}
        >
          {tab.content}
        </RadixTabs.Content>
      ))}
    </RadixTabs.Root>
  );
}
