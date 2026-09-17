import {
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Grid,
  LinearProgress,
  Stack,
  Typography
} from "@mui/material";
import type { LearningContentStat } from "./types";

export function LearningDashboard({ items }: { items: LearningContentStat[] }) {
  return (
    <Stack spacing={3}>
      <Grid container spacing={2}>
        {items.map((item) => (
          <Grid key={item.content_id} size={{ xs: 12, sm: 6, lg: 4 }}>
            <Card sx={{ height: "100%" }}>
              <CardActionArea href={item.detail_url} sx={{ height: "100%" }}>
                <CardContent>
                  <Stack spacing={1.5}>
                    <Typography variant="h6">{item.title}</Typography>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography color="text.secondary" variant="body2">
                        AC {item.ac}問
                      </Typography>
                      <Typography color="text.secondary" variant="body2">
                        {item.ac_rate}%
                      </Typography>
                    </Stack>
                    <LinearProgress
                      variant="determinate"
                      value={item.ac_rate}
                      sx={{ height: 9, borderRadius: 999 }}
                    />
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                      <Chip size="small" label={`全 ${item.total}問`} />
                      <Chip size="small" label={`着手 ${item.attempted}問`} variant="outlined" />
                    </Stack>
                  </Stack>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Stack>
  );
}
