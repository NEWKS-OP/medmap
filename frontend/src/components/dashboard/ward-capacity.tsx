"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface WardCapacityProps {
  wards: { ward: string; patients: number }[];
}

export function WardCapacity({ wards }: WardCapacityProps) {
  const max = Math.max(1, ...wards.map((w) => w.patients));
  const total = wards.reduce((s, w) => s + w.patients, 0);
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle>Patients by Ward</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {wards.map((ward, i) => {
          const pct = Math.round((ward.patients / max) * 100);
          return (
            <motion.div
              key={ward.ward}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="space-y-1.5"
            >
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium">{ward.ward}</span>
                <span className="font-semibold tabular-nums text-muted-foreground">
                  {ward.patients}
                  <span className="font-normal ml-1">({Math.round((ward.patients / Math.max(1, total)) * 100)}%)</span>
                </span>
              </div>
              <Progress value={pct} className="h-1.5 [&>div]:bg-primary" />
            </motion.div>
          );
        })}
      </CardContent>
    </Card>
  );
}
