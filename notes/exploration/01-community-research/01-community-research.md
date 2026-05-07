# F1 related project suggestion in the field of deep learning & Time-series

**Community:** r/F1Technical · **Posted by:** u/RustinChole1 · **Score:** 62 upvotes · **Date:** August 27, 2025

**Source:** https://www.reddit.com/r/F1Technical/comments/1n1gt7o/f1_related_project_suggestion_in_the_field_of/

---

Hello guys, I'm working as a deep-learning / Time-series intern and for my college project I am planning to work on something which is complex enough to build and related to both what I'm working on + formula one because I'm very much interested to work on it.

  
teams performance analysis, strategies prediction or anything else we can do with telemetry data that'll be convincing enough when I present it .

Thank you in advanced

---

## Comments (9 fetched)

---

**u/AutoModerator** · 1 points · Aug 27, 2025

We remind everyone that this sub is for technical discussions.

If you are new to the sub, please [read our rules](https://www.reddit.com/r/F1Technical/about/rules/) and [comment etiquette post.](https://www.reddit.com/r/F1Technical/comments/zlo2qf/comment_etiquette_update/?utm_source=share&utm_medium=web2x&context=3)


*I am a bot, and this action was performed automatically. Please [contact the moderators of this subreddit](/message/compose/?to=/r/F1Technical) if you have any questions or concerns.*

---

**u/highchillerdeluxe** · 19 points · Aug 27, 2025

I would advice against historical data analysis because of the lack or sparcity of data. There have been only around 800 drivers and only about 1000 races in the history of F1. That's pretty small when you look at something specific like drivers, teams, tracks etc. On top of that, you have a bunch of changing variables, such as weather (temperature, wind, rain), car generation, tire choices, etc so you have a very high dimensionality. It will be tough to learn anything meaningful from that. While certainly fun questions, they fall more into the simple statistics analysis rather than deep-learning in my opinion.

With telemetry data (actual acceleration, braking, steering angles, g-forces, etc) you could do a lot though as you would have immense amount of data correlated to only a few constants (drivers, teams, tracks). Hence I suggest on focusing on a few constants, like a specific driver or track, and get all telemetry data. Than you can try to make lap time predictions on the fly (eg 1/4 through the lap, what will be the drivers time?), overtake predictions (eg comparing telemetry of two close cars, can you predict an overtake?), tire degredation modeling, perfect lap time, and such. Another idea would be to compare driving styles based on brake and acceleration patterns and how they relate to lap times. In essence, its what F1 teams already do anyway in house.

As a general tip, try to keep the questions simple and chose the once that have lots of comparable data.

---

> **u/RustinChole1** · 2 points

> " Another idea would be to compare driving styles based on brake and acceleration patterns and how they relate to lap times. "
> 
> I made a similar project like this: comparing tracks based on a drivers throttle and brakes input but yeah  
> what you said about historical data makes sense
> 
> I'll look into what more I can do with telemetry

> > **u/URZ_** · 3 points

> > Just be aware that the public telemetry data is noisy, occasionally in the extreme.

> **u/Technical_f1** · 4 points

> I have a question. Where can I find telemetry data

**u/Aduttya** · 6 points · Aug 27, 2025

Would recommend going to strategies that would be a good deep learning project.

---

> **u/RustinChole1** · 3 points

> yeah I was thinking of some system which can be useful in performance analysis, but can you elaborate the usecase a bit more

> > **u/Aduttya** · 2 points

> > The strategies depend upon the making calls under variables like tyer wear, safety car, rivals and multiple others. 
> > 
> > A model trained on historical data to help make these decisions.

> > > **u/Astelli** · 4 points

> > > Easier said than done.
> > > 
> > > At a track like Zandvoort you've only got 3 races in the dry to try and train a model from, all of them with different cars and in different conditions.
> > > 
> > > Especially if OP is interested in deep learning, that size of dataset probably won't be sufficient to train any sensible model.

**u/Ujjwal_Raj** · 4 points · Aug 28, 2025

Where are you getting this data ?
PS - Even I would love to work o  something like that.

---

**u/No-Will6114** · 4 points · Aug 28, 2025

Wait how did you get the internship??? I was working on the strategy project but had to drop it (personal reasons). I would like to know how you entered motorsport from the computer science field??please if you can guide 🙏

---

> **u/RustinChole1** · 3 points

> Hey there, I think there was a misunderstanding
> The company where I'm working at are in multiple racing championships like we and imsa but I'm not a part of those teams , I work in the research department and sometimes get to work on those data

**u/AlarmedJuggernaut598** · 3 points · Aug 28, 2025

This is actually a really cool idea! I was thinking something similar like maybe doing a project around driver braking & throttle patterns and clustering them to compare styles. Could be fun to combine that with race strategy simulations too.

I mess around with F1 insights sometimes, so this thread definitely gave me a few new ideas to try. Love seeing posts like this here!

---

**u/el-jollof** · 5 points · Aug 28, 2025

I have been seeing a lot of telemetry and analysis projects recently.if you want to be unique i suggest you make a system that helps engineers attain data on how to preserve tires by analysing tire temp,wear,compound,driving style,max speed,pressure etc.like for example according to your inputs,the output will give a results table that tell you how much life and performance you can expect under x speed y pressure and z driving style under each scenario....
Just giving suggestion i am not aware of how complex or possible it is but if it is do-able its worth a shot.it would be a good deep learning project since there are lots of variables

---

**u/bibonacci2** · 2 points · Aug 28, 2025

It’ll largely depend on what data you have access to. Are you interning with a team or partner company?

Things on the strategy side are going to be very difficult to test in any meaningful way.  Possibly you could do something like predicting gaps, if you have the data (like the stuff that AWS do for the broadcast).

---

> **u/RustinChole1** · 2 points

> The company which I work at are in wec, imsa and super gt but sadly not in F1

**u/tag-2002** · 1 points · Aug 28, 2025

Would you mind telling the name of your company? Is it an European or American company?

---
