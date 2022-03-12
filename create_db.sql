/****** Object:  Table [dbo].[bt_actual]    Script Date: 3/12/2022 2:36:34 PM ******/

/****** Object:  Database [batterytracker]    Script Date: 3/12/2022 2:38:52 PM ******/
CREATE DATABASE [batterytracker]  (EDITION = 'Basic', SERVICE_OBJECTIVE = 'Basic', MAXSIZE = 2 GB) WITH CATALOG_COLLATION = SQL_Latin1_General_CP1_CI_AS;
GO

ALTER DATABASE [batterytracker] SET ANSI_NULL_DEFAULT OFF 
GO

ALTER DATABASE [batterytracker] SET ANSI_NULLS OFF 
GO

ALTER DATABASE [batterytracker] SET ANSI_PADDING OFF 
GO

ALTER DATABASE [batterytracker] SET ANSI_WARNINGS OFF 
GO

ALTER DATABASE [batterytracker] SET ARITHABORT OFF 
GO

ALTER DATABASE [batterytracker] SET AUTO_SHRINK OFF 
GO

ALTER DATABASE [batterytracker] SET AUTO_UPDATE_STATISTICS ON 
GO

ALTER DATABASE [batterytracker] SET CURSOR_CLOSE_ON_COMMIT OFF 
GO

ALTER DATABASE [batterytracker] SET CONCAT_NULL_YIELDS_NULL OFF 
GO

ALTER DATABASE [batterytracker] SET NUMERIC_ROUNDABORT OFF 
GO

ALTER DATABASE [batterytracker] SET QUOTED_IDENTIFIER OFF 
GO

ALTER DATABASE [batterytracker] SET RECURSIVE_TRIGGERS OFF 
GO

ALTER DATABASE [batterytracker] SET AUTO_UPDATE_STATISTICS_ASYNC OFF 
GO

ALTER DATABASE [batterytracker] SET ALLOW_SNAPSHOT_ISOLATION ON 
GO

ALTER DATABASE [batterytracker] SET PARAMETERIZATION SIMPLE 
GO

ALTER DATABASE [batterytracker] SET READ_COMMITTED_SNAPSHOT ON 
GO

ALTER DATABASE [batterytracker] SET  MULTI_USER 
GO

ALTER DATABASE [batterytracker] SET ENCRYPTION ON
GO

ALTER DATABASE [batterytracker] SET QUERY_STORE = ON
GO

ALTER DATABASE [batterytracker] SET QUERY_STORE (OPERATION_MODE = READ_WRITE, CLEANUP_POLICY = (STALE_QUERY_THRESHOLD_DAYS = 7), DATA_FLUSH_INTERVAL_SECONDS = 900, INTERVAL_LENGTH_MINUTES = 60, MAX_STORAGE_SIZE_MB = 10, QUERY_CAPTURE_MODE = AUTO, SIZE_BASED_CLEANUP_MODE = AUTO, MAX_PLANS_PER_QUERY = 200, WAIT_STATS_CAPTURE_MODE = ON)
GO

/*** The scripts of database scoped configurations in Azure should be executed inside the target database connection. ***/
GO

-- ALTER DATABASE SCOPED CONFIGURATION SET MAXDOP = 8;
GO

ALTER DATABASE [batterytracker] SET  READ_WRITE 
GO


SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[bt_actual](
	[color] [nchar](10) NULL,
	[UID] [varchar](max) NULL,
	[height] [float] NULL,
	[seconds] [float] NULL
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

CREATE TABLE [dbo].[bt_plan](
	[ID] [varchar](max) NULL,
	[Batch] [nchar](10) NULL,
	[Operator] [text] NULL,
	[Sequence] [text] NULL,
	[StartTime] [datetime] NULL,
	[EndTime] [datetime] NULL,
	[Iterations] [int] NULL
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

CREATE TABLE [dbo].[bt_video](
	[UID] [varchar](max) NULL,
	[URL] [nvarchar](max) NULL,
	[HTML] [nvarchar](max) NULL
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
